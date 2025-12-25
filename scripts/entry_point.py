"""
Entry point for PyInstaller builds.
This wrapper uses absolute imports to avoid the 'no known parent package' error.
Launches the Web Control Panel which provides a UI to manage the application.
"""
import sys
import os
import multiprocessing

# CRITICAL: This must be called FIRST in the main module for PyInstaller on Windows.
# Without this, multiprocessing will cause infinite process spawning because
# child processes re-execute the main script instead of just running the target function.
if __name__ == "__main__":
    multiprocessing.freeze_support()

# Ensure src is in the path for imports
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    application_path = os.path.dirname(sys.executable)
else:
    # Running as script
    application_path = os.path.dirname(os.path.abspath(__file__))

# Add the project root to sys.path
if application_path not in sys.path:
    sys.path.insert(0, application_path)

# Now import and run the web control panel
from src.web_control_panel import main as control_panel_main

if __name__ == "__main__":
    control_panel_main()

