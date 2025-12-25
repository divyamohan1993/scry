@echo off
setlocal EnableDelayedExpansion
:: Navigate to project root (parent of scripts folder)
cd /d "%~dp0.."

:: ============================================================================
:: SCRY - NUCLEAR STOP
:: Terminates ALL Scry-related processes - stuck, crashed, multiple instances
:: This is the "kill everything" script
:: ============================================================================

:: Ensure log directory exists
if not exist "_runtime\logs" mkdir "_runtime\logs"
set "LOGFILE=_runtime\logs\stop.log"
echo [%date% %time%] ====== STOP INITIATED ====== > "%LOGFILE%"

echo.
echo   ========================================
echo     SCRY - Terminating All Processes
echo   ========================================
echo.

:: ============================================================================
:: 1. KILL BY PID FILE (if exists)
:: ============================================================================
if exist "_runtime\app.pid" (
    set /p PID=<_runtime\app.pid
    echo [STOP] Killing PID from file: !PID!
    echo [%date% %time%] Killing PID: !PID! >> "%LOGFILE%"
    taskkill /PID !PID! /F /T >nul 2>&1
    del "_runtime\app.pid" >nul 2>&1
)

:: ============================================================================
:: 2. KILL ALL PYTHON PROCESSES WITH SCRY-RELATED COMMAND LINES
:: ============================================================================
echo [STOP] Killing Scry-related Python processes...

:: Kill by specific module names
for %%M in (src.main web_control_panel gui_control_panel control_panel validate_env) do (
    echo   - Terminating %%M processes...
    echo [%date% %time%] Killing %%M >> "%LOGFILE%"
    wmic process where "CommandLine like '%%~M%%' and (name='python.exe' or name='pythonw.exe')" call terminate >nul 2>&1
)

:: Kill by project path patterns
for %%P in (screen-reader-auto-answer scry Scry) do (
    echo   - Terminating processes with path: %%P
    echo [%date% %time%] Killing path pattern: %%P >> "%LOGFILE%"
    wmic process where "CommandLine like '%%~P%%' and (name='python.exe' or name='pythonw.exe')" call terminate >nul 2>&1
)

:: ============================================================================
:: 3. KILL FLASK SERVERS ON COMMON PORTS
:: ============================================================================
echo [STOP] Killing Flask servers on ports 5000, 5001, 8080...

for %%P in (5000 5001 8080) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%%P ^| findstr LISTENING 2^>nul') do (
        if not "%%a"=="" (
            echo   - Killing process on port %%P: PID %%a
            echo [%date% %time%] Killing port %%P PID: %%a >> "%LOGFILE%"
            taskkill /PID %%a /F >nul 2>&1
        )
    )
)

:: ============================================================================
:: 4. KILL ALL PYTHONW.EXE (windowless Python - used by silent launchers)
:: Be aggressive here since pythonw is mainly used by our silent mode
:: ============================================================================
echo [STOP] Killing all windowless Python (pythonw.exe)...
echo [%date% %time%] Killing all pythonw.exe >> "%LOGFILE%"
taskkill /F /IM pythonw.exe >nul 2>&1

:: ============================================================================
:: 5. KILL WSCRIPT RUNNING OUR VBS FILES
:: ============================================================================
echo [STOP] Killing VBS script hosts...
for %%V in (Scry.vbs Scry_Stop.vbs scry_launcher) do (
    wmic process where "CommandLine like '%%~V%%' and name='wscript.exe'" call terminate >nul 2>&1
)

:: ============================================================================
:: 6. CLEANUP ZOMBIE CMD PROCESSES (from batch scripts)
:: ============================================================================
echo [STOP] Killing orphaned batch processes...
for %%B in (scry_launcher.bat scry.bat start.bat) do (
    wmic process where "CommandLine like '%%~B%%' and name='cmd.exe'" call terminate >nul 2>&1
)

:: ============================================================================
:: 7. FORCE KILL ANY REMAINING PYTHON WITH OUR PATHS
:: Using taskkill with window title matching (backup method)
:: ============================================================================
echo [STOP] Final cleanup pass...
taskkill /F /FI "WINDOWTITLE eq *scry*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq *Scry*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq *flask*" >nul 2>&1

:: ============================================================================
:: 8. CLEANUP TEMP/LOCK FILES
:: ============================================================================
echo [STOP] Cleaning up lock files...
if exist "_runtime\*.pid" del "_runtime\*.pid" >nul 2>&1
if exist "_runtime\*.lock" del "_runtime\*.lock" >nul 2>&1

:: ============================================================================
:: DONE
:: ============================================================================
echo [%date% %time%] ====== STOP COMPLETE ====== >> "%LOGFILE%"

echo.
echo   ========================================
echo     All Scry processes terminated!
echo   ========================================
echo.
echo   Killed:
echo     - Main application (src.main)
echo     - Web control panel (Flask)
echo     - GUI control panel
echo     - All pythonw.exe instances
echo     - VBS script hosts
echo     - Orphaned batch processes
echo     - Flask servers on ports 5000/5001/8080
echo.

exit /b 0
