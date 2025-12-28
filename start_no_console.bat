@echo off
REM Start Daisho without console window
if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" main.py
) else (
    echo Virtual environment not found. Please run setup.bat first.
    pause
)
