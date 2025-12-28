@echo off
echo Starting Daisho (代書)...

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

REM Run the application
python main.py

REM Keep console open if there was an error
if errorlevel 1 (
    echo.
    echo Application exited with error.
    pause
)
