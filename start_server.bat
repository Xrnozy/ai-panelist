@echo off
REM ============================================================================
REM AI Panel Review System - Startup Script (CUDA 12.8 Nightly for RTX 5060 Ti)
REM ============================================================================
REM Features:
REM - Checks Python installation
REM - Creates/activates virtual environment
REM - Installs PyTorch nightly CUDA 12.8 with force-reinstall (RTX 5060 Ti Blackwell)
REM - Installs all dependencies from requirements.txt
REM - Verifies GPU/CUDA availability
REM - Starts FastAPI server on 0.0.0.0:8000
REM ============================================================================
setlocal EnableDelayedExpansion
chcp 65001 >nul

echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║    🤖 AI Panel Review System - Startup (GPU-ONLY MODE)                 ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

REM Get script directories
set "SCRIPT_DIR=%~dp0"
set "AI_SERVER_DIR=%SCRIPT_DIR%ai_server"
set "VENV_DIR=%SCRIPT_DIR%venv"

echo [1/7] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.9+
    echo    https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% found

echo.
echo [2/7] Checking/Creating virtual environment...
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
echo [3/7] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)
echo ✅ Virtual environment activated

echo.
echo [4/7] Upgrading pip...
python -m pip install --upgrade pip setuptools wheel >nul 2>&1
echo ✅ Pip upgraded

echo.
echo [5/7] Checking PyTorch CUDA 12.8 installation (RTX 5060 Ti - Blackwell CC 12.0)...

REM Check if PyTorch is already installed and working
python -c "import torch; torch.cuda.is_available()" >nul 2>&1
if %errorlevel% equ 0 (
    REM PyTorch is already installed, get version
    for /f "tokens=*" %%i in ('python -c "import torch; print(torch.__version__)"') do set TORCH_VERSION=%%i
    echo ✅ PyTorch cu128 nightly already installed: !TORCH_VERSION! (skipping reinstall)
) else (
    REM PyTorch not installed, install it now
    echo ℹ️  PyTorch not found, installing now...
    echo    This may take 2-3 minutes on first run...
    pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128 --no-cache-dir --no-deps
    if errorlevel 1 (
        echo ❌ Failed to install PyTorch cu128 nightly
        echo ℹ️  Make sure you have 5GB+ free disk space
        pause
        exit /b 1
    )
    echo ✅ PyTorch cu128 nightly installed
)

echo.
echo [6/7] Installing dependencies from requirements.txt...
cd /d "%AI_SERVER_DIR%"
pip install -r requirements.txt --no-cache-dir
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)
echo ✅ All dependencies installed

echo.
echo [7/7] Verifying GPU/CUDA availability...
python -c "import torch; cuda_avail = torch.cuda.is_available(); print('✅ GPU: ' + (torch.cuda.get_device_name(0) if cuda_avail else 'CPU')); print('   CUDA: ' + (str(torch.version.cuda) if cuda_avail else 'N/A'))"

echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║  ✅ Startup Complete! Starting FastAPI Server...                       ║
echo ║                                                                          ║
echo ║  📍 API:              http://127.0.0.1:8000                             ║
echo ║  📚 API Docs:         http://127.0.0.1:8000/docs                       ║
echo ║  💚 Health Check:     http://127.0.0.1:8000/health                     ║
echo ║                                                                          ║
echo ║  🔑 API Key:          aipanelist_secret_key_2026                        ║
echo ║                                                                          ║
echo ║  ℹ️  Keep this terminal open while running                              ║
echo ║  ℹ️  Press Ctrl+C to stop the server                                    ║
echo ║                                                                          ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

REM Start FastAPI server with all operations on GPU (NO RELOAD - preserve GPU context)
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1

pause
