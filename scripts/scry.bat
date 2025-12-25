@echo off
setlocal
:: Navigate to project root (parent of scripts folder)
cd /d "%~dp0.."

:: ============================================================================
:: SCRY - DEVELOPER LAUNCHER (with console output)
:: "Divine your answers."
:: For silent launch without console, use Scry.vbs in root folder
:: This version shows console output for debugging
:: ============================================================================

echo.
echo   ========================================
echo     SCRY - Control Panel (Dev Mode)
echo   ========================================
echo.

:: Check Python - this is the ONLY prerequisite
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.10+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%I in ('python --version 2^>^&1') do set PYTHON_VERSION=%%I
echo [INFO] Found Python %PYTHON_VERSION%

:: Ensure minimal runtime directory exists
if not exist "_runtime" mkdir "_runtime"

:: Quick bootstrap: Install Flask for the control panel if not present
:: The control panel will handle full dependency installation when user clicks Start
echo [INFO] Checking control panel requirements...
python -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo [SETUP] Installing control panel dependencies...
    pip install flask flask-cors python-dotenv -q
    if %errorlevel% neq 0 (
        echo [WARN] Could not install dependencies globally.
        echo [INFO] Will try with virtual environment...
        
        :: Create venv if needed
        if not exist "_runtime\venv" (
            echo [SETUP] Creating virtual environment...
            python -m venv _runtime\venv
        )
        
        :: Install in venv
        call _runtime\venv\Scripts\pip install flask flask-cors python-dotenv -q
    )
)

:: Launch web control panel
:: If venv exists, use it; otherwise use system Python
echo.
echo [START] Opening control panel in browser...
echo [INFO] The control panel will install all other dependencies when you click Start.
echo.

if exist "_runtime\venv\Scripts\python.exe" (
    _runtime\venv\Scripts\python src\web_control_panel.py
) else (
    python src\web_control_panel.py
)

pause
