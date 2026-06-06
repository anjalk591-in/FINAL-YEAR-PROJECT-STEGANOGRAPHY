@echo off
echo ========================================
echo StegAnalyzer Pro - Windows Setup
echo ========================================
echo.

echo [1/5] Creating required directories...
mkdir instance 2>nul
mkdir media\uploads 2>nul
mkdir media\cache 2>nul
mkdir media\reports 2>nul
mkdir media\visualizations 2>nul
echo Done!
echo.

echo [2/5] Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    echo Make sure Python 3.8+ is installed
    pause
    exit /b 1
)
echo Done!
echo.

echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat
echo Done!
echo.

echo [4/5] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Done!
echo.

echo [5/5] Initializing database...
set FLASK_APP=run.py
flask init-db
flask seed-db
echo Done!
echo.

echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo To start the application:
echo   1. Activate virtual environment: venv\Scripts\activate
echo   2. Run: python run.py
echo   3. Open: http://localhost:5000
echo.
pause