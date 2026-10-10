# Whisper Talk

Dictée vocale 100 % locale pour Windows, basée sur [Whisper](https://github.com/openai/whisper)
via [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
Un raccourci clavier lance l'enregistrement, un second l'arrête : le texte transcrit est
collé directement dans le champ actif (chat d'un agent, éditeur, navigateur…).

Aucune donnée ne quitte la machine (seul le modèle est téléchargé au premier lancement).

## Installation

Prérequis : Windows, Python 3.10+, un micro.

```bash
pip install -r requirements.txt
```

Puis créer le raccourci sur le Bureau (lancement sans console) :

```bash
powershell -ExecutionPolicy Bypass -File install_shortcuts.ps1
```

Options du script : `-Startup` ajoute aussi un lancement automatique à l'ouverture de
session, `-Remove` supprime les raccourcis.

## Utilisation

Double-cliquer sur **Whisper Talk** sur le Bureau. Une icône de micro apparaît dans la
zone de notification (près de l'horloge) ; sa couleur indique l'état :

| Couleur | État |
|---|---|
| 🔵 Bleu | Chargement du modèle |
| ⚪ Gris | Prêt |
| 🔴 Rouge | Enregistrement |
| 🟠 Orange | Transcription |

### Raccourcis globaux

| Raccourci | Action |
|---|---|
| `Ctrl+Alt+Espace` | Démarrer / arrêter l'enregistrement (à l'arrêt : transcription + collage) |
| `Ctrl+Alt+X` | Annuler l'enregistrement ou la transcription en cours |
| `Ctrl+Alt+C` | Recopier la dernière transcription dans le presse-papiers |
| `Ctrl+Alt+Q` | Quitter |

Le clic droit sur l'icône donne les mêmes actions, plus l'ouverture du journal.
Un double-clic sur l'icône démarre / arrête l'enregistrement.

Le texte est inséré par copier-coller (`Ctrl+V`) dans le champ qui a le focus clavier ;
l'ancien contenu du presse-papiers (texte) est restauré ensuite.

## Options

Lancées en ligne de commande (`python whisper_flow.py …`) ou ajoutées aux arguments du
raccourci :

| Option | Effet |
|---|---|
| `--model NOM` | `tiny`, `base`, `small` (défaut), `medium`, `large-v3`, `large-v3-turbo` |
| `--language CODE` | Langue (`fr` par défaut), ou `auto` pour la détection |
| `--no-paste` | Copier seulement, sans coller |
| `--keep-clipboard` | Laisser la transcription dans le presse-papiers après collage |

Sur CPU, `small` est un bon compromis (≈ 4 s pour une phrase sur un i7 de 11ᵉ génération).
Les modèles plus gros sont plus précis mais nettement plus lents.

## Débogage

- `whisper_flow.bat` lance l'outil avec une console visible.
- Le journal est écrit dans `whisper_talk.log`.

## Limites connues

- Pour coller dans une application lancée **en administrateur**, Whisper Talk doit aussi
  être lancé en administrateur (restriction de Windows).
- L'annulation pendant la transcription d'un long passage empêche le collage, mais le
  calcul déjà engagé se termine (l'icône peut rester orange quelques secondes).
- Un enregistrement est arrêté automatiquement après 5 minutes.
- Seul le texte du presse-papiers est restauré après collage (pas les images).
