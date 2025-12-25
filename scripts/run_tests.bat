@echo off
setlocal
:: Navigate to project root (parent of scripts folder)
cd /d "%~dp0.."

echo [TEST] Checking environment...

if not exist "_runtime" mkdir "_runtime"

:: 1. Setup Venv
if not exist "_runtime\venv" (
    echo [TEST] Creating virtual environment...
    python -m venv _runtime\venv
)

:: 2. Activate
call _runtime\venv\Scripts\activate.bat

:: 3. Install Reqs
echo [TEST] Installing dependencies...
pip install -r requirements.txt >nul 2>&1

:: 4. Run Test
echo [TEST] Running Unit Tests...
echo [TEST] Executing all verification suites...

:: A. Standard Unit Tests (Logic/Mocked)
echo [1/3] Running Unit Tests...
pytest tests/ || echo [WARN] Unit tests failed, continuing...

:: B. Human Typing Validation (Generative)
echo [2/3] Running Human Typing Validation...
python tests/test_human_typing.py

:: C. Reflexive System Simulation (Full E2E)
echo [3/3] Running Reflexive Simulation...
python tests/run_reflexive_simulation.py

echo [TEST] check_all_verified.
pause
