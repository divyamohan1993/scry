#!/bin/bash

# ============================================================================
# SCRY - STARTUP SCRIPT (Linux/Mac)
# Idempotent Setup & Execution (DevSecOps Best Practices)
# ============================================================================

set -e

# Navigate to project root (parent of scripts folder)
cd "$(dirname "$0")/.."

# 0. Ensure Single Instance (Auto-Close previous)
# We use bash to run it to ensure compatibility
bash scripts/stop.sh >/dev/null 2>&1

# 1. Initialize Logs
mkdir -p _runtime/logs
LOGFILE="_runtime/logs/startup.log"
echo "[START] Startup initiated at $(date)" > "$LOGFILE"
export PYTHONPYCACHEPREFIX="$(pwd)/_runtime/pycache"
mkdir -p _runtime/pycache

# 2. Check Python
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo "[ERROR] Python 3 is not installed."
    exit 1
fi

echo "[INFO] Using $($PYTHON_CMD --version)"
echo "[INFO] Using $($PYTHON_CMD --version)" >> "$LOGFILE"

# 3. Setup Virtual Environment
if [ ! -d "_runtime/venv" ]; then
    echo "[SETUP] Creating virtual environment in _runtime/venv..."
    $PYTHON_CMD -m venv _runtime/venv >> "$LOGFILE" 2>&1
    echo "[INFO] Virtual environment created."
fi

# 4. Activate Environment
source _runtime/venv/bin/activate

# 5. Install Dependencies
echo "[SETUP] Syncing dependencies..."
python -m pip install --upgrade pip >> "$LOGFILE" 2>&1
if [ -f "requirements.txt" ]; then
    python -m pip install -r requirements.txt >> "$LOGFILE" 2>&1
    echo "[INFO] Dependencies synced."
fi

# 6. Configuration Check
if [ ! -f ".env" ]; then
    echo "[CONFIG] .env file not found."
    echo "================================================================"
    echo " GEMINI API KEY SETUP"
    echo "================================================================"
    read -p "Enter API Key: " API_KEY
    echo "GEMINI_API_KEY=$API_KEY" > .env
    echo "[INFO] API Key saved."
fi

# 7. Launch Application
RUN_MODE=$(python -c "import src.config; print('VISIBLE' if src.config.DEVELOPER_MODE else 'STEALTH')")

echo "[RUN] Launching in $RUN_MODE mode..."
echo "[RUN] Launching in $RUN_MODE mode..." >> "$LOGFILE"

if [ "$RUN_MODE" == "VISIBLE" ]; then
    python -m src.main
else
    nohup python -m src.main > _runtime/logs/app.log 2>&1 &
    echo "[INFO] Running in background. Logs in _runtime/logs/app.log"
    echo "[INFO] Run 'pkill -f src.main' to stop (or creating stop.sh is recommended)"
fi
