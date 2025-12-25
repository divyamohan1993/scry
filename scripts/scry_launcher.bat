@echo off
setlocal EnableDelayedExpansion
:: Navigate to project root (parent of scripts folder)
cd /d "%~dp0.."

:: ============================================================================
:: SCRY - SILENT LAUNCHER (Called by Scry.vbs)
:: "Divine your answers."
:: Auto-installs Python if missing, then starts the control panel
:: ============================================================================

:: Ensure minimal runtime directory exists for logging
if not exist "_runtime" mkdir "_runtime"
if not exist "_runtime\logs" mkdir "_runtime\logs"

:: Log file for debugging if needed
set "LOGFILE=_runtime\logs\launcher.log"
echo [%date% %time%] Launcher started > "%LOGFILE%"

:: ============================================================================
:: PYTHON CHECK & AUTO-INSTALL
:: ============================================================================
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] Python not found, initiating install... >> "%LOGFILE%"
    
    :: Show a message to the user (this is the one visible interaction)
    msg * "Python is not installed. Scry will now download and install Python automatically. This may take a few minutes."
    
    :: Determine architecture
    if "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
        set "PYTHON_URL=https://www.python.org/ftp/python/3.12.1/python-3.12.1-amd64.exe"
    ) else (
        set "PYTHON_URL=https://www.python.org/ftp/python/3.12.1/python-3.12.1.exe"
    )
    
    set "PYTHON_INSTALLER=_runtime\python_installer.exe"
    
    echo [%date% %time%] Downloading Python from %PYTHON_URL%... >> "%LOGFILE%"
    
    :: Download Python installer using PowerShell
    powershell -NoProfile -Command ^
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; " ^
        "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'" >> "%LOGFILE%" 2>&1
    
    if not exist "%PYTHON_INSTALLER%" (
        echo [%date% %time%] Failed to download Python installer >> "%LOGFILE%"
        msg * "Failed to download Python. Please install Python 3.10+ manually from https://python.org"
        exit /b 1
    )
    
    echo [%date% %time%] Installing Python silently... >> "%LOGFILE%"
    
    :: Install Python silently with PATH option
    :: /quiet = silent install
    :: InstallAllUsers=0 = install for current user only (no admin needed)
    :: PrependPath=1 = add to PATH
    :: Include_pip=1 = include pip
    start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0
    
    echo [%date% %time%] Python installation completed >> "%LOGFILE%"
    
    :: Clean up installer
    del "%PYTHON_INSTALLER%" >nul 2>&1
    
    :: Refresh environment variables (PATH)
    :: We need to reload PATH to find the newly installed Python
    for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USER_PATH=%%b"
    set "PATH=%USER_PATH%;%PATH%"
    
    :: Verify installation
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [%date% %time%] Python still not found after install >> "%LOGFILE%"
        msg * "Python was installed but requires a system restart. Please restart your computer and try again."
        exit /b 1
    )
    
    echo [%date% %time%] Python verified successfully >> "%LOGFILE%"
    msg * "Python installed successfully! Starting Scry..."
)

:: Log Python version
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [%date% %time%] Found %%i >> "%LOGFILE%"

:: ============================================================================
:: BOOTSTRAP FLASK FOR CONTROL PANEL
:: ============================================================================
python -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] Installing control panel dependencies... >> "%LOGFILE%"
    pip install flask flask-cors python-dotenv -q >> "%LOGFILE%" 2>&1
    if %errorlevel% neq 0 (
        :: Try with virtual environment
        if not exist "_runtime\venv" (
            echo [%date% %time%] Creating virtual environment... >> "%LOGFILE%"
            python -m venv _runtime\venv >> "%LOGFILE%" 2>&1
        )
        call _runtime\venv\Scripts\pip install flask flask-cors python-dotenv -q >> "%LOGFILE%" 2>&1
    )
)

:: ============================================================================
:: LAUNCH WEB CONTROL PANEL
:: ============================================================================
echo [%date% %time%] Starting web control panel... >> "%LOGFILE%"

:: If venv exists, use it; otherwise use system Python
if exist "_runtime\venv\Scripts\pythonw.exe" (
    start "" _runtime\venv\Scripts\pythonw src\web_control_panel.py
) else (
    start "" pythonw src\web_control_panel.py
)

echo [%date% %time%] Launcher complete >> "%LOGFILE%"
