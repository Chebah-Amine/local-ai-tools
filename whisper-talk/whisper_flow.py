"""Whisper Talk : dictée vocale locale avec Whisper (faster-whisper).

Tourne dans la zone de notification (icône près de l'horloge) :
  gris = prêt · rouge = enregistrement · orange = transcription · bleu = chargement

Raccourcis globaux :
  Ctrl+Alt+Espace  -> démarrer / arrêter l'enregistrement
                      à l'arrêt : transcription, nettoyage IA (Mistral, si une clé est
                      configurée), puis collage dans le champ actif
  Ctrl+Alt+X       -> annuler (enregistrement ou transcription en cours)
  Ctrl+Alt+C       -> recopier la dernière transcription dans le presse-papiers
  Ctrl+Alt+Q       -> quitter
"""

import argparse
import ctypes
import logging
import os
import queue
import sys
import threading
import time
import winsound

import keyboard
import numpy as np
import pyperclip
import pystray
import sounddevice as sd
from PIL import Image, ImageDraw

SAMPLE_RATE = 16000
MAX_SECONDS = 300  # arrêt automatique d'un enregistrement oublié
HERE = os.path.dirname(os.path.abspath(__file__))

# Nettoyage IA partagé avec l'outil voisin text-polish (même prompt, même modèle).
sys.path.insert(0, os.path.join(HERE, "..", "text-polish"))
from text_polish import load_api_key, polish  # noqa: E402
LOG_PATH = os.path.join(HERE, "whisper_talk.log")

log = logging.getLogger("whisper_talk")

LOADING, IDLE, RECORDING, TRANSCRIBING = "loading", "idle", "recording", "transcribing"
COLORS = {LOADING: "#3b82f6", IDLE: "#6b7280", RECORDING: "#ef4444", TRANSCRIBING: "#f59e0b"}
LABELS = {LOADING: "chargement du modèle…", IDLE: "prêt", RECORDING: "enregistrement…",
          TRANSCRIBING: "transcription…"}


def beep(freq, ms):
    """Bip non bloquant (winsound.Beep peut prendre ~0,5 s)."""
    threading.Thread(target=winsound.Beep, args=(freq, ms), daemon=True).start()


def make_icon(color):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, 60, 60), fill=color)
    # micro stylisé
    d.rounded_rectangle((25, 14, 39, 38), radius=7, fill="white")
    d.arc((19, 24, 45, 46), 0, 180, fill="white", width=3)
    d.line((32, 46, 32, 52), fill="white", width=3)
    return img


def single_instance():
    """Retourne un handle de mutex nommé, ou None si une instance tourne déjà."""
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\WhisperTalkSingleInstance")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        return None
    return handle


class WhisperTalk:
    def __init__(self, model_name, language, paste, keep_clipboard, api_key):
        self.model_name = model_name
        self.language = language
        self.paste = paste
        self.keep_clipboard = keep_clipboard
        self.api_key = api_key  # None : pas de nettoyage IA
        self.polish_enabled = api_key is not None
        self.model = None

        self.state = LOADING
        self.stream = None
        self.frames = queue.Queue()
        self.started_at = 0.0
        self.last_text = ""
        self.cancel_event = threading.Event()

        # Toutes les actions passent par une file traitée par un seul thread :
        # pas de courses entre raccourcis, ordre garanti.
        self.commands = queue.Queue()
        self.worker = threading.Thread(target=self._worker, name="worker", daemon=True)
        self.icon = None

    # --- état / icône -----------------------------------------------------
    def set_state(self, state):
        self.state = state
        log.info("État : %s", state)
        if self.icon:
            self.icon.icon = make_icon(COLORS[state])
            self.icon.title = f"Whisper Talk — {LABELS[state]}"
            self.icon.update_menu()

    def notify(self, msg):
        log.warning(msg)
        if self.icon:
            try:
                self.icon.notify(msg, "Whisper Talk")
            except Exception:
                pass

    # --- commandes (appelées depuis raccourcis / menu) --------------------
    def post(self, cmd):
        if cmd == "cancel":
            # Annulation immédiate, même si le worker est occupé à transcrire.
            self.cancel_event.set()
        self.commands.put(cmd)

    def _worker(self):
        try:
            from faster_whisper import WhisperModel
            log.info("Chargement du modèle %s", self.model_name)
            self.model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
            # Ignorer les raccourcis pressés pendant le chargement (sauf « quitter »).
            while not self.commands.empty():
                if self.commands.get_nowait() == "quit":
                    return
            self.set_state(IDLE)
        except Exception:
            log.exception("Échec du chargement du modèle")
            self.notify("Impossible de charger le modèle Whisper (voir whisper_talk.log).")
            return

        while True:
            try:
                cmd = self.commands.get(timeout=1.0)
            except queue.Empty:
                if self.state == RECORDING and time.time() - self.started_at > MAX_SECONDS:
                    self.notify(f"Enregistrement arrêté automatiquement après {MAX_SECONDS // 60} min.")
                    cmd = "toggle"
                else:
                    continue
            if cmd == "quit":
                break
            try:
                if cmd == "toggle":
                    if self.state == IDLE:
                        self._start()
                    elif self.state == RECORDING:
                        self._stop_and_transcribe()
                elif cmd == "cancel":
                    self._cancel()
                elif cmd == "copy":
                    if self.last_text:
                        pyperclip.copy(self.last_text)
                        log.info("Dernière transcription copiée")
            except Exception as e:
                log.exception("Erreur pendant '%s'", cmd)
                self._close_stream()
                self.set_state(IDLE)
                self.notify(f"Erreur : {e}")
        self._close_stream()

    # --- audio -------------------------------------------------------------
    def _callback(self, indata, frames, t, status):
        if status:
            log.debug("Statut audio : %s", status)
        self.frames.put(indata.copy())

    def _start(self):
        self.cancel_event.clear()
        self.frames = queue.Queue()
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                dtype="float32", callback=self._callback)
        try:
            stream.start()
        except Exception:
            stream.close()
            raise
        self.stream = stream
        self.started_at = time.time()
        self.set_state(RECORDING)
        beep(880, 120)

    def _close_stream(self):
        """Ferme le micro s'il est ouvert. Sans effet sinon (idempotent)."""
        stream, self.stream = self.stream, None
        if stream is not None:
            try:
                stream.stop()
            finally:
                stream.close()
            log.info("Micro fermé")

    def _collect_audio(self):
        chunks = []
        while True:
            try:
                chunks.append(self.frames.get_nowait())
            except queue.Empty:
                break
        return np.concatenate(chunks).flatten() if chunks else np.zeros(0, np.float32)

    def _cancel(self):
        if self.state == RECORDING:
            self._close_stream()
            self._collect_audio()  # libère la mémoire
            self.set_state(IDLE)
            beep(300, 200)
            log.info("Enregistrement annulé")
        # Pendant TRANSCRIBING, cancel_event suffit (vérifié entre les segments).

    def _stop_and_transcribe(self):
        self._close_stream()
        audio = self._collect_audio()
        beep(440, 120)
        duration = len(audio) / SAMPLE_RATE
        if duration < 0.3:
            log.info("Trop court (%.2fs), ignoré", duration)
            self.set_state(IDLE)
            return

        self.cancel_event.clear()
        self.set_state(TRANSCRIBING)
        try:
            t0 = time.time()
            segments, _ = self.model.transcribe(audio, language=self.language,
                                                beam_size=5, vad_filter=True)
            parts = []
            for s in segments:  # générateur : la transcription se fait ici
                if self.cancel_event.is_set():
                    log.info("Transcription annulée")
                    beep(300, 200)
                    return
                parts.append(s.text.strip())
            text = " ".join(parts).strip()
            log.info("Transcrit %.1fs d'audio en %.1fs : %r", duration, time.time() - t0, text)
            if text and self.polish_enabled and not self.cancel_event.is_set():
                text = self._polish(text)
            if text and not self.cancel_event.is_set():
                self.last_text = text
                self._output(text)
        finally:
            self.set_state(IDLE)

    def _polish(self, text):
        """Nettoyage IA ; en cas d'échec, on colle la transcription brute plutôt que rien."""
        try:
            t0 = time.time()
            cleaned = polish(text, self.api_key)
            log.info("Nettoyé en %.1fs : %r", time.time() - t0, cleaned)
            return cleaned
        except Exception as e:
            log.exception("Échec du nettoyage IA")
            self.notify(f"Nettoyage IA impossible, texte brut collé : {e}")
            return text

    # --- sortie ------------------------------------------------------------
    def _output(self, text):
        if not self.paste:
            pyperclip.copy(text)
            return
        previous = pyperclip.paste()
        pyperclip.copy(text)
        # Attendre que Ctrl/Alt/Maj soient relâchés avant de coller (max 2 s).
        deadline = time.time() + 2
        while time.time() < deadline and any(keyboard.is_pressed(k) for k in ("ctrl", "alt", "shift")):
            time.sleep(0.02)
        keyboard.send("ctrl+v")
        if not self.keep_clipboard:
            time.sleep(0.3)  # laisser l'application lire le presse-papiers
            pyperclip.copy(previous)

    def _toggle_polish(self):
        self.polish_enabled = not self.polish_enabled
        log.info("Nettoyage IA : %s", "activé" if self.polish_enabled else "désactivé")

    # --- cycle de vie ------------------------------------------------------
    def run(self):
        def label_toggle(_):
            return "Arrêter l'enregistrement" if self.state == RECORDING else "Démarrer l'enregistrement"

        menu = pystray.Menu(
            pystray.MenuItem(lambda _: f"État : {LABELS[self.state]}", None, enabled=False),
            pystray.MenuItem(label_toggle, lambda: self.post("toggle"), default=True,
                             enabled=lambda _: self.state in (IDLE, RECORDING)),
            pystray.MenuItem("Annuler\tCtrl+Alt+X", lambda: self.post("cancel"),
                             enabled=lambda _: self.state in (RECORDING, TRANSCRIBING)),
            pystray.MenuItem("Copier la dernière transcription\tCtrl+Alt+C", lambda: self.post("copy"),
                             enabled=lambda _: bool(self.last_text)),
            pystray.MenuItem("Nettoyage IA (Mistral)", self._toggle_polish,
                             checked=lambda _: self.polish_enabled,
                             enabled=lambda _: self.api_key is not None),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Ouvrir le journal", lambda: os.startfile(LOG_PATH)),
            pystray.MenuItem("Quitter\tCtrl+Alt+Q", lambda: self.icon.stop()),
        )
        self.icon = pystray.Icon("whisper_talk", make_icon(COLORS[LOADING]),
                                 f"Whisper Talk — {LABELS[LOADING]}", menu)

        keyboard.add_hotkey("ctrl+alt+space", lambda: self.post("toggle"), suppress=True)
        keyboard.add_hotkey("ctrl+alt+x", lambda: self.post("cancel"), suppress=True)
        keyboard.add_hotkey("ctrl+alt+c", lambda: self.post("copy"), suppress=True)
        keyboard.add_hotkey("ctrl+alt+q", lambda: self.icon.stop(), suppress=True)

        def setup(icon):
            icon.visible = True
            self.worker.start()

        try:
            self.icon.run(setup=setup)  # bloque jusqu'à « Quitter »
        finally:
            self.shutdown()

    def shutdown(self):
        log.info("Arrêt…")
        keyboard.unhook_all()
        self.cancel_event.set()
        self.commands.put("quit")
        if self.worker.is_alive():
            self.worker.join(timeout=5)
        self._close_stream()  # au cas où le worker n'aurait pas pu le faire
        log.info("Arrêté proprement")


def main():
    p = argparse.ArgumentParser(description="Dictée vocale locale avec Whisper")
    p.add_argument("--model", default="small",
                   help="tiny, base, small, medium, large-v3, large-v3-turbo (défaut : small)")
    p.add_argument("--language", default="fr", help="code langue, ou 'auto' (défaut : fr)")
    p.add_argument("--no-paste", action="store_true",
                   help="ne pas coller automatiquement, seulement copier")
    p.add_argument("--keep-clipboard", action="store_true",
                   help="laisser la transcription dans le presse-papiers après collage")
    p.add_argument("--key-file", help="fichier contenant la clé API Mistral (nettoyage IA)")
    p.add_argument("--no-polish", action="store_true", help="désactiver le nettoyage IA")
    args = p.parse_args()

    handlers = [logging.FileHandler(LOG_PATH, encoding="utf-8")]
    if sys.stdout is not None:  # None sous pythonw
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(level=logging.INFO, handlers=handlers,
                        format="%(asctime)s %(levelname)s %(message)s")

    mutex = single_instance()
    if mutex is None:
        ctypes.windll.user32.MessageBoxW(None, "Whisper Talk est déjà lancé (icône près de l'horloge).",
                                         "Whisper Talk", 0x40)
        return

    api_key = None
    if not args.no_polish:
        try:
            api_key = load_api_key(args.key_file)
        except Exception as e:
            log.warning("Nettoyage IA désactivé : %s", e)

    try:
        WhisperTalk(args.model, None if args.language == "auto" else args.language,
                    paste=not args.no_paste, keep_clipboard=args.keep_clipboard, api_key=api_key).run()
    except Exception:
        log.exception("Erreur fatale")
        raise
    finally:
        ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()
