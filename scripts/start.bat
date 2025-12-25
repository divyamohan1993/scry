@echo off
setlocal
:: Navigate to project root (parent of scripts folder)
cd /d "%~dp0.."

:: ============================================================================
:: SCRY - STARTUP SCRIPT
:: "Divine your answers."
:: Idempotent Setup & Execution (DevSecOps Best Practices)
:: ============================================================================

:: 0. Ensure Single Instance (Auto-Close previous)
call scripts\stop.bat >nul 2>&1

:: 1. Setup Runtime Environment
if not exist "_runtime" mkdir "_runtime"
if not exist "_runtime\logs" mkdir "_runtime\logs"
set "LOGFILE=_runtime\logs\startup.log"
echo [START] Startup initiated at %date% %time% > "%LOGFILE%"
set "PYTHONPYCACHEPREFIX=%cd%\_runtime\pycache"
if not exist "_runtime\pycache" mkdir "_runtime\pycache"

:: 2. Check Python Availability
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)
for /f "tokens=2" %%I in ('python --version 2^>^&1') do set PYTHON_VERSION=%%I
echo [INFO] Found Python version: %PYTHON_VERSION%
echo [INFO] Found Python version: %PYTHON_VERSION% >> "%LOGFILE%"

:: 3. Setup Virtual Environment (Idempotent)
if not exist "_runtime\venv" (
    echo [SETUP] Creating virtual environment in _runtime\venv...
    python -m venv _runtime\venv >> "%LOGFILE%" 2>&1
    if not exist "_runtime\venv\Scripts\activate.bat" (
        echo [ERROR] Failed to create venv. See _runtime\logs\startup.log for details.
        pause
        exit /b 1
    )
    echo [INFO] Virtual environment created.
) else (
    echo [INFO] Using existing virtual environment.
)

:: 4. Activate Environment
call _runtime\venv\Scripts\activate.bat

:: 5. Install Dependencies (Idempotent)
echo [SETUP] Syncing dependencies...
python -m pip install --upgrade pip >> "%LOGFILE%" 2>&1
if exist requirements.txt (
    python -m pip install -r requirements.txt >> "%LOGFILE%" 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies. Check _runtime\logs\startup.log.
        pause
        exit /b 1
    )
    echo [INFO] Dependencies synced.
)

:: 6. Security & Configuration Check (secrets management)
echo [CONFIG] Checking environment configuration...
python src\validate_env.py
if %errorlevel% neq 0 (
    echo [ERROR] Configuration check failed.
    pause
    exit /b 1
)

:: 7. Launch Application
:: Check if developer mode or stealth needed based on config (or default)
for /f "tokens=*" %%a in ('python -c "import src.config; print('VISIBLE' if src.config.DEVELOPER_MODE else 'STEALTH')" 2^>nul') do set RUN_MODE=%%a

if "%RUN_MODE%"=="" set RUN_MODE=STEALTH

echo [RUN] Launching in %RUN_MODE% mode...
echo [RUN] Launching in %RUN_MODE% mode... >> "%LOGFILE%"

if "%RUN_MODE%"=="VISIBLE" (
    python -m src.main
) else (
    start "" pythonw -m src.main
    echo [INFO] Running in background. Logs in _runtime\logs\app.log
    echo [INFO] Run stop.bat to terminate.
    ping -n 4 127.0.0.1 >nul
)
