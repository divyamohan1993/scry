#!/bin/bash

# ============================================================================
# SCRY - STOP SCRIPT
# Forcefully terminates the application
# ============================================================================

# Navigate to project root (parent of scripts folder)
cd "$(dirname "$0")/.."

echo "[STOP] Initiating shutdown sequence..."

# 1. Try to kill via PID file
if [ -f "_runtime/app.pid" ]; then
    PID=$(cat "_runtime/app.pid")
    if ps -p $PID > /dev/null 2>&1; then
        echo "[STOP] Found PID file. Killing PID: $PID"
        kill -9 $PID
        rm "_runtime/app.pid"
    else
        echo "[STOP] PID file found but process $PID is not running. Cleaning up."
        rm "_runtime/app.pid"
    fi
fi

# 2. Cleanup via Process Search (Failsafe)
echo "[STOP] Scanning for lingering instances..."
# We use pkill to find the specific python module execution
pkill -9 -f "src.main" || true

echo "[STOP] All instances terminated."
