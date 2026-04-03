@echo off
REM ============================================================================
REM AI Panel Review System - Start Website Only
REM ============================================================================
REM Starts a local web server for the website on port 3000
REM ============================================================================

echo.
echo ==================== AI Panel Review System ====================
echo Website Server
echo.

cd /d "%~dp0website"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo.
echo Starting website on http://127.0.0.1:3000
echo.
echo Configuration:
echo - Edit API URL and API Key in the website interface
echo - Make sure the FastAPI server is running (run start_server.bat)
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start Python HTTP server
python -m http.server 3000

pause
