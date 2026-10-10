# Text Polish

Nettoyage de texte dicté pour Windows, via l'[API Mistral](https://console.mistral.ai)
(offre gratuite). Un raccourci clavier nettoie le texte sélectionné, ou tout le champ si rien
n'est sélectionné : hésitations (« euh », « du coup »…), répétitions, faux départs et
auto-corrections (« 15h, enfin 16h » donne « 16h »), orthographe, ponctuation. Le résultat
remplace directement le texte dans le champ actif.

Fonctionne avec n'importe quel outil de dictée. [Whisper Talk](../whisper-talk) l'utilise aussi
pour nettoyer chaque dictée automatiquement avant de la coller.

## Installation

Prérequis : Windows, Python 3.10+, une clé API Mistral (gratuite) enregistrée dans un fichier texte.

```bash
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File install_shortcuts.ps1 -KeyFile C:\chemin\mistral-api-key.txt
```

Le script :
- lance Text Polish immédiatement ;
- l'ajoute au démarrage de Windows (il tourne en arrière-plan, rien à lancer ni à quitter) ;
- ajoute un raccourci **Text Polish** au menu Démarrer, pour le relancer après un arrêt.

Options : `-Desktop` ajoute un raccourci sur le Bureau, `-Remove` arrête l'appli et supprime
les raccourcis. Relancer le script redémarre l'appli avec la nouvelle configuration.

La clé peut aussi être fournie par la variable d'environnement `MISTRAL_API_KEY`
(ou `MISTRAL_API_KEY_FILE` pour un chemin de fichier).

## Utilisation

| Raccourci        | Action                                                              |
|------------------|---------------------------------------------------------------------|
| `Ctrl+Alt+P`     | Nettoyer la sélection, ou tout le champ s'il n'y a pas de sélection |
| `Ctrl+Alt+Z`     | Annuler le dernier nettoyage (envoie `Ctrl+Z` à l'application)      |
| `Ctrl+Alt+Maj+P` | Quitter Text Polish                                                 |

Icône dans la zone de notification : gris = prêt, orange = traitement. Un bip aigu signale la
fin, un bip grave une erreur (détail en notification et dans `text_polish.log`).

Dans le Gestionnaire des tâches, l'appli n'a pas de fenêtre : elle apparaît dans
**Processus en arrière-plan**, sous le nom de l'interpréteur Python (`pythonw.exe` ou
`pythonw3.10.exe`).

## Options

```bash
python text_polish.py --model mistral-small-latest   # autre modèle Mistral
python text_polish.py --text "euh bonjour du coup je voulais euh dire"   # test sans raccourci
```

Le modèle par défaut, `ministral-8b-latest`, répond en environ 0,5 s et est disponible sur l'offre
gratuite. Les modèles plus gros (`mistral-small-latest`…) peuvent y être limités (erreur 429).

## Fonctionnement et limites

- Le texte est lu et remplacé par copier-coller (`Ctrl+C` / `Ctrl+V`). L'application cible doit
  les supporter. Le presse-papiers (texte) est restauré ensuite (`--keep-clipboard` pour garder
  le texte nettoyé).
- Le texte est envoyé à l'API Mistral (serveurs en Europe) : ne pas l'utiliser sur du contenu
  confidentiel.
- Le modèle ne répond jamais au contenu : une consigne dictée (« écris-moi un poème ») est
  nettoyée, pas exécutée. Garde-fou supplémentaire : une réponse bien plus longue que l'original
  est rejetée et le texte reste intact.
- Pour agir sur une application lancée **en administrateur**, Text Polish doit aussi être lancé
  en administrateur (restriction de Windows).
- `text_polish.bat` lance l'outil avec une console visible (débogage).
