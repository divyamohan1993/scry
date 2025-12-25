@echo off
setlocal EnableDelayedExpansion
:: Navigate to project root (parent of scripts folder)
cd /d "%~dp0.."

:: ============================================================================
:: SCRY - PACKAGE FOR DISTRIBUTION
:: Creates a clean zip file for sharing to other computers
:: Excludes all sensitive, generated, and dynamic files
:: ============================================================================

echo.
echo   ========================================
echo     SCRY - Packaging for Distribution
echo   ========================================
echo.

:: Set output filename with timestamp
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set DATE=%%c%%a%%b)
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (set TIME=%%a%%b)
set "ZIPNAME=Scry_%DATE%.zip"

:: Check for PowerShell (required for zip creation)
powershell -Command "exit" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PowerShell is required for creating zip files.
    pause
    exit /b 1
)

echo [INFO] Creating distribution package: %ZIPNAME%
echo.

:: Create a temporary directory for packaging
set "TEMP_DIR=_runtime\package_temp"
if exist "%TEMP_DIR%" rd /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%"

echo [COPY] Copying clean source files...

:: Copy only the files that should be distributed
:: Root files
copy "Scry.vbs" "%TEMP_DIR%\" >nul
copy "Scry_Stop.vbs" "%TEMP_DIR%\" >nul
copy "README.md" "%TEMP_DIR%\" >nul
copy ".env.example" "%TEMP_DIR%\" >nul
copy ".gitignore" "%TEMP_DIR%\" >nul
copy ".flake8" "%TEMP_DIR%\" >nul
copy "pyproject.toml" "%TEMP_DIR%\" >nul
copy "requirements.txt" "%TEMP_DIR%\" >nul

:: Scripts folder
mkdir "%TEMP_DIR%\scripts"
xcopy "scripts\*.bat" "%TEMP_DIR%\scripts\" /q >nul
xcopy "scripts\*.sh" "%TEMP_DIR%\scripts\" /q >nul
xcopy "scripts\*.py" "%TEMP_DIR%\scripts\" /q >nul

:: Source folder (excluding __pycache__)
mkdir "%TEMP_DIR%\src"
xcopy "src\*.py" "%TEMP_DIR%\src\" /q >nul
if exist "src\assets" (
    mkdir "%TEMP_DIR%\src\assets"
    xcopy "src\assets\*" "%TEMP_DIR%\src\assets\" /q >nul 2>&1
)
if exist "src\utils" (
    mkdir "%TEMP_DIR%\src\utils"
    xcopy "src\utils\*.py" "%TEMP_DIR%\src\utils\" /q >nul
)
if exist "src\prompts" (
    mkdir "%TEMP_DIR%\src\prompts"
    xcopy "src\prompts\*" "%TEMP_DIR%\src\prompts\" /q >nul
)

:: Tests folder (excluding generated test pages and cache)
mkdir "%TEMP_DIR%\tests"
xcopy "tests\*.py" "%TEMP_DIR%\tests\" /q >nul 2>&1
if exist "tests\templates" (
    mkdir "%TEMP_DIR%\tests\templates"
    xcopy "tests\templates\*" "%TEMP_DIR%\tests\templates\" /q >nul 2>&1
)

:: GitHub workflows
if exist ".github" (
    mkdir "%TEMP_DIR%\.github"
    xcopy ".github" "%TEMP_DIR%\.github\" /s /e /q >nul 2>&1
)

:: Agent workflows (if exists)
if exist ".agent" (
    mkdir "%TEMP_DIR%\.agent"
    xcopy ".agent" "%TEMP_DIR%\.agent\" /s /e /q >nul 2>&1
)

:: Remote folder (if exists and needed for distribution)
if exist "remote" (
    mkdir "%TEMP_DIR%\remote"
    xcopy "remote\*.py" "%TEMP_DIR%\remote\" /q >nul 2>&1
    xcopy "remote\*.html" "%TEMP_DIR%\remote\" /q >nul 2>&1
    xcopy "remote\*.js" "%TEMP_DIR%\remote\" /q >nul 2>&1
    xcopy "remote\*.css" "%TEMP_DIR%\remote\" /q >nul 2>&1
    xcopy "remote\*.json" "%TEMP_DIR%\remote\" /q >nul 2>&1
    xcopy "remote\*.md" "%TEMP_DIR%\remote\" /q >nul 2>&1
    if exist "remote\templates" (
        mkdir "%TEMP_DIR%\remote\templates"
        xcopy "remote\templates\*" "%TEMP_DIR%\remote\templates\" /s /e /q >nul 2>&1
    )
    if exist "remote\static" (
        mkdir "%TEMP_DIR%\remote\static"
        xcopy "remote\static\*" "%TEMP_DIR%\remote\static\" /s /e /q >nul 2>&1
    )
)

echo [ZIP] Creating zip archive...

:: Delete old zip if exists
if exist "%ZIPNAME%" del "%ZIPNAME%"

:: Create zip using PowerShell
powershell -NoProfile -Command ^
    "Compress-Archive -Path '%TEMP_DIR%\*' -DestinationPath '%ZIPNAME%' -Force"

if %errorlevel% neq 0 (
    echo [ERROR] Failed to create zip file!
    rd /s /q "%TEMP_DIR%"
    pause
    exit /b 1
)

:: Cleanup temp directory
rd /s /q "%TEMP_DIR%"

:: Get file size
for %%A in ("%ZIPNAME%") do set SIZE=%%~zA
set /a SIZE_KB=%SIZE%/1024

echo.
echo   ========================================
echo     PACKAGING COMPLETE!
echo   ========================================
echo.
echo   File: %ZIPNAME%
echo   Size: %SIZE_KB% KB
echo.
echo   This package includes:
echo     - Main launcher (Scry.vbs)
echo     - All source code
echo     - Scripts and configuration
echo     - Tests
echo.
echo   This package EXCLUDES:
echo     - .env (secrets)
echo     - _runtime folder (venv, logs, cache)
echo     - __pycache__ folders
echo     - Any .exe files
echo     - IDE settings
echo.
echo   To use on new computer:
echo     1. Extract the zip
echo     2. Double-click Scry.vbs
echo     3. Click Start - everything installs automatically!
echo.

pause
