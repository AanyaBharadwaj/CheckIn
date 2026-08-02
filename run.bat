@echo off

:: CheckIn Real-Time Voice Server Launcher

echo ================================
echo   CheckIn Real-Time Voice
echo ================================
echo.

:: Check if we're in the right directory
if not exist "server.py" (
    echo Error: Please run this script from the project root directory
    exit /b 1
)

:: Check for .env file
if not exist ".env" (
    echo Error: .env file not found
    echo Please create .env with DEEPGRAM_API_KEY and GEMINI_API_KEY
    exit /b 1
)

:: Check for required packages
echo Checking dependencies...
python -c "import pipecat" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo Starting voice server on ws://localhost:8765
echo Starting frontend on http://localhost:8080
echo.
echo Press Ctrl+C to stop
echo ================================
echo.

:: Start frontend server in background
start /b python -m http.server 8080 --directory docs

:: Start voice server in foreground
python server.py

:: Clean up frontend server on exit
taskkill /f /im python.exe /fi "WINDOWTITLE eq *http.server*" 2>nul



