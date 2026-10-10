@echo off
rem Lancement avec console (debug). Pour l'usage normal, utiliser le raccourci du Bureau.
title Text Polish (debug)
cd /d "%~dp0"
python text_polish.py %*
pause
