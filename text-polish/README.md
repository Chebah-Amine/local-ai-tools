# Text Polish

Nettoyage de texte 100 % local pour Windows, basé sur un modèle servi par [Ollama](https://ollama.com).
Un raccourci clavier nettoie le texte sélectionné (ou tout le champ si rien n'est sélectionné) :
hésitations (« euh », « du coup »…), répétitions, faux départs, orthographe, ponctuation.
Le résultat remplace directement le texte dans le champ actif.

Pensé pour compléter [Whisper Talk](../whisper-talk) : dicter, puis `Ctrl+Alt+P`.
Aucune donnée ne quitte la machine.

## Installation

Prérequis : Windows, Python 3.10+, [Ollama](https://ollama.com/download).

```bash
ollama pull qwen2.5:3b
pip install -r requirements.txt
```

Raccourci sur le Bureau (lancement sans console) :

```bash
powershell -ExecutionPolicy Bypass -File install_shortcuts.ps1
```

Options : `-Startup` (lancement à l'ouverture de session), `-Remove` (supprime les raccourcis).

## Utilisation

| Raccourci    | Action                                                        |
|--------------|---------------------------------------------------------------|
| `Ctrl+Alt+P` | Nettoyer la sélection, ou tout le champ s'il n'y a pas de sélection |
| `Ctrl+Alt+Z` | Annuler le dernier nettoyage (envoie `Ctrl+Z` à l'application) |

Icône dans la zone de notification : gris = prêt, orange = traitement. Un bip aigu signale la fin.

## Options

```bash
python text_polish.py --model mistral:7b      # autre modèle Ollama
python text_polish.py --text "euh bonjour du coup je voulais euh dire"   # test sans raccourci
```

Le modèle par défaut (`qwen2.5:3b`) est un bon compromis vitesse/qualité en français sur CPU.
Pour une meilleure qualité (plus lent) : `mistral:7b` ou `qwen2.5:7b`.

## Limites

- Fonctionne via `Ctrl+C` / `Ctrl+V` : l'application cible doit les supporter. Le presse-papiers
  est restauré après l'opération (`--keep-clipboard` pour le conserver).
- Une réponse du modèle beaucoup plus longue que l'original est rejetée (texte laissé intact).
