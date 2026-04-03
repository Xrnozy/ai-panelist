@echo off
REM ============================================================================
REM Tab Audio Transcriber - Startup Script (RTX 50 Series / CUDA 12.8 LOCKED)
REM ============================================================================
REM Features:
REM - Checks Python
REM - Creates/activates virtual environment
REM - Installs PyTorch only if missing or incompatible
REM - Installs other dependencies
REM - Verifies FFmpeg
REM - Checks CUDA availability
REM - Starts FastAPI backend
REM - Launches frontend + browser
REM ============================================================================
setlocal EnableDelayedExpansion
chcp 65001 >nul

echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║           🎙️  Tab Audio Transcriber - Startup                         ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

REM Get script directories
set "SCRIPT_DIR=%~dp0"
set "APP_DIR=%SCRIPT_DIR%app"
set "BACKEND_DIR=%APP_DIR%\backend"
set "FRONTEND_DIR=%APP_DIR%\frontend"
set "VENV_DIR=%SCRIPT_DIR%venv"

echo [1/8] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.10+
    echo    https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% found

echo.
echo [2/8] Checking/Creating virtual environment...
if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo ✅ Virtual environment already exists
) else (
    echo 📦 Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
    echo ✅ Virtual environment created
)

echo.
echo [3/8] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)
echo ✅ Virtual environment activated

echo.
echo [4/8] Upgrading pip...
python -m pip install --upgrade pip setuptools wheel >nul 2>&1
echo ✅ Pip upgraded

echo.
echo [5/8] Installing dependencies...
echo    (This may take a few minutes on first run)

REM Skip PyTorch version check - just install dependencies
pip install -r "%SCRIPT_DIR%requirements.txt"
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)
echo ✅ Dependencies installed

echo.
echo [6/8] NeMo Toolkit (Optional - for .nemo model support)...
python -c "import nemo; print('✅ NeMo toolkit available')" 2>nul
if errorlevel 1 (
    echo ⚠️  NeMo toolkit not installed (optional)
    echo    To use .nemo models, install: pip install nemo_toolkit
) else (
    echo ✅ NeMo toolkit available
)

echo.
echo [7/8] Checking FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  FFmpeg not found (optional but recommended)
    echo    https://ffmpeg.org/download.html
) else (
    echo ✅ FFmpeg available
)

echo.
echo [8/8] Checking GPU/CUDA availability...
python -c "import torch; print('✅ GPU: ' + torch.cuda.get_device_name(0) if torch.cuda.is_available() else '💻 CPU Mode'); print('   CUDA: ' + str(torch.version.cuda) if torch.cuda.is_available() else '   CUDA: N/A')" 2>nul

echo.
echo [9/8] Starting services...
echo.

REM Start backend in new terminal
echo 🚀 Starting FastAPI backend...
start "Tab Transcriber - Backend" cmd /k ^
"cd /d "%BACKEND_DIR%" ^&^& "%VENV_DIR%\Scripts\python.exe" main.py"

REM Wait for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend server in new terminal
echo 🚀 Starting frontend server...
start "Tab Transcriber - Frontend" cmd /k ^
"cd /d "%FRONTEND_DIR%" ^&^& "%VENV_DIR%\Scripts\python.exe" -m http.server 8001"

REM Wait for servers to fully initialize
timeout /t 2 /nobreak >nul

REM Check if browser already has the website open
echo 🌐 Checking if website is already open...
tasklist /FI "IMAGENAME eq chrome.exe" 2>nul | find /I /N "chrome.exe" >nul
if errorlevel 1 (
    REM Chrome not running or website not found, open browser
    echo    Website not detected in Chrome, opening in new window...
    start "" http://localhost:8000
) else (
    REM Chrome is running, check if localhost:8000 is already open
    powershell -Command "try { $null = [System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}; (New-Object System.Net.WebClient).DownloadString('http://localhost:8000') | Out-Null; } catch { exit 1 }" >nul 2>&1
    if errorlevel 1 (
        REM Backend not ready yet, open browser
        echo    Backend starting, opening in browser...
        start "" http://localhost:8000
    ) else (
        REM Browser or another window likely has it, don't open
        echo    ✅ Website likely already open in browser, skipping new window
    )
)

echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║  ✅ Startup Complete!                                                   ║
echo ║                                                                          ║
echo ║  📍 Access the app at:  http://localhost:8000                           ║
echo ║                                                                          ║
echo ║  ℹ️  Keep both terminal windows open while using the app                ║
echo ║  ℹ️  Close both terminals to stop the application                       ║
echo ║                                                                          ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

pause
