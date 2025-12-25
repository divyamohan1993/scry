@echo off
setlocal
:: Navigate to project root (parent of scripts folder)
cd /d "%~dp0.."

echo [BUILD] Starting build process...
set "PYTHONPYCACHEPREFIX=%cd%\_runtime\pycache"
if not exist "_runtime\pycache" mkdir "_runtime\pycache"

:: Ensure environment is ready
if not exist "_runtime\venv" (
    echo [ERROR] Virtual environment not found. Please run scripts\start.bat first.
    pause
    exit /b 1
)

call _runtime\venv\Scripts\activate.bat

:: Install PyInstaller if missing
pip install pyinstaller

echo [BUILD] Cleaning previous builds...
if exist "_runtime\build" rd /s /q "_runtime\build"
if exist "_runtime\dist" rd /s /q "_runtime\dist"
if exist "_runtime\Scry.spec" del "_runtime\Scry.spec"

:: Note: --key encryption was removed in PyInstaller v6.0
:: Alternative obfuscation can be done with tools like PyArmor if needed

echo [BUILD] Compiling Application with obfuscation...
:: --noconsole: Don't show terminal window (stealth mode)
:: --onefile: Bundle everything into a single .exe
:: --name: Name of the output file
:: --key: Encrypts Python bytecode with AES-256 (requires pycryptodome)
:: --strip: Remove debug symbols
:: --exclude-module: Exclude dev/test modules
:: --hidden-import: Explicitly include dependencies that might be missed
:: --workpath: Store temp build files in _runtime/build
:: --distpath: Store output exe in _runtime/dist
:: --specpath: Store spec file in _runtime
pyinstaller --noconsole --onefile --clean --name "Scry" ^
    --exclude-module pytest ^
    --exclude-module black ^
    --exclude-module flake8 ^
    --exclude-module bandit ^
    --exclude-module isort ^
    --collect-all flask ^
    --collect-all flask_cors ^
    --hidden-import="mss" ^
    --hidden-import="pyautogui" ^
    --hidden-import="PIL" ^
    --hidden-import="keyboard" ^
    --hidden-import="cv2" ^
    --hidden-import="requests" ^
    --hidden-import="tkinter" ^
    --hidden-import="tkinter.simpledialog" ^
    --hidden-import="tkinter.messagebox" ^
    --hidden-import="flask" ^
    --hidden-import="flask.json" ^
    --hidden-import="flask.templating" ^
    --hidden-import="flask_cors" ^
    --hidden-import="werkzeug" ^
    --hidden-import="werkzeug.serving" ^
    --hidden-import="werkzeug.routing" ^
    --hidden-import="jinja2" ^
    --hidden-import="dotenv" ^
    --hidden-import="webbrowser" ^
    --hidden-import="markupsafe" ^
    --hidden-import="click" ^
    --hidden-import="itsdangerous" ^
    --workpath "_runtime\build" ^
    --distpath "_runtime\dist" ^
    --specpath "_runtime" ^
    scripts\entry_point.py

if %errorlevel% neq 0 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo [BUILD] Build Success!
echo [INFO] executable is located at _runtime\dist\Scry.exe
echo [INFO] You can distribute this file.

pause
