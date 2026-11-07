@echo off
cd /d "%~dp0"
python editeur_sauvegarde.py
if errorlevel 1 pause
