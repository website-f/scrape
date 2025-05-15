@echo off
cd /d "%~dp0"

echo Starting Flask server...
start "" cmd /k "python test.py"

timeout /t 3 >nul

echo Opening browser...
start http://127.0.0.1:5050
