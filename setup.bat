@echo off
echo ==========================================
echo Daisho (代書) Setup
echo ==========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10 or later from python.org
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo WARNING: Some dependencies failed to install.
    echo The application may not work correctly.
)

echo.
echo ==========================================
echo Setup complete!
echo ==========================================
echo.
echo To start the application, run: start.bat
echo.
echo NOTE: For GPU acceleration with NVIDIA cards, run:
echo   pip uninstall torch
echo   pip install torch --index-url https://download.pytorch.org/whl/cu121
echo.
pause
