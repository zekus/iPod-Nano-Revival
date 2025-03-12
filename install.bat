@echo off
REM Installation script for YouTube Music to iPod Nano Transfer Tool (Windows)

echo Installing YouTube Music to iPod Nano Transfer Tool...

REM Check if Python 3 is installed
python --version 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo Python 3 is required but not installed. Please install Python 3 and try again.
    exit /b 1
)

REM Check if pip is installed
pip --version 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo pip is required but not installed. Please install pip and try again.
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Create necessary directories
echo Creating necessary directories...
if not exist temp mkdir temp
if not exist downloads mkdir downloads
if not exist converted mkdir converted

echo.
echo Installation complete!
echo.
echo To run the application:
echo   1. Activate the virtual environment: venv\Scripts\activate.bat
echo   2. Run the GUI application: python run.py
echo   3. Or run the CLI application: python run.py --cli --url "https://www.youtube.com/watch?v=VIDEO_ID"
echo.
echo For more information, see the README.md file.

pause
