@echo off
cd /d "%~dp0"
python -m pip install -q -r requirements.txt
where pythonw >nul 2>nul
if %ERRORLEVEL%==0 (
    start "" pythonw main.py
) else (
    python main.py
    pause
)
