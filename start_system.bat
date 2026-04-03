@echo off
REM ============================================================================
REM AI Panel Review System - Quick Start
REM ============================================================================
REM This script starts the server and opens the website
REM ============================================================================

echo.
echo ==================== AI Panel Review System ====================
echo Quick Start Launcher
echo.

REM Change to ai_server directory
cd /d "%~dp0ai_server"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

REM Install requirements
echo Installing dependencies (this may take a few minutes)...
python -m pip install -q -r requirements.txt --upgrade

echo.
echo ✓ Starting API Server...
echo.

REM Start server in background
start "" cmd /k "python -m uvicorn main:app --host 0.0.0.0 --port 8000"

REM Wait for server to start
timeout /t 5 /nobreak

REM Open website
echo.
echo ✓ Opening website in browser...
start "" http://127.0.0.1:3000

REM Open server documentation
start "" http://127.0.0.1:8000/docs

echo.
echo ==================== System Running ====================
echo.
echo Website: http://127.0.0.1:3000
echo   - Open index.html in the website/ folder
echo     or use: python -m http.server 3000 --directory website
echo.
echo API Server: http://127.0.0.1:8000
echo API Docs: http://127.0.0.1:8000/docs
echo Health: http://127.0.0.1:8000/health
echo.
echo API Key: aipanelist_secret_key_2026
echo.
echo To connect from hackathon laptop:
echo   1. Use Cloudflare Tunnel: cloudflared tunnel --url http://localhost:8000
echo   2. Replace http://localhost:8000 with tunnel URL in website
echo.
pause
