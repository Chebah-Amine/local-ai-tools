@echo off
rem Lancement avec console (debug). Pour l'usage normal, utiliser le raccourci du Bureau.
title Whisper Talk (debug)
cd /d "%~dp0"
python whisper_flow.py %*
pause
