#!/bin/bash
# Navigate to project root (parent of scripts folder)
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -f "_runtime/venv/bin/activate" ]; then
    source _runtime/venv/bin/activate
else
    echo "[WARNING] Virtual environment not found. Using system Python."
fi

# Run the control panel
python3 src/control_panel.py || python src/control_panel.py

read -p "Press Enter to exit..."
