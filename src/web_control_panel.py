"""
Scry - Web Control Panel
A modern web-based admin control panel for managing environment variables,
with start/stop/test controls and live terminal output streaming.
"""

import os
import sys
import json
import subprocess
import threading
import time
import queue
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# Detect if running as frozen PyInstaller executable
IS_FROZEN = getattr(sys, 'frozen', False)

# Flask for web server
try:
    from flask import Flask, render_template_string, jsonify, request, Response
    from flask_cors import CORS
except ImportError:
    if not IS_FROZEN:
        print("Installing required packages...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "flask-cors", "-q"])
        from flask import Flask, render_template_string, jsonify, request, Response
        from flask_cors import CORS
    else:
        raise ImportError("Flask not bundled in frozen executable")

try:
    from dotenv import set_key
except ImportError:
    if not IS_FROZEN:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv", "-q"])
        from dotenv import set_key
    else:
        raise ImportError("python-dotenv not bundled in frozen executable")

# Setup paths
if IS_FROZEN:
    # When frozen, the exe is in _runtime/dist, project root is 2 levels up
    PROJECT_ROOT = Path(sys.executable).resolve().parent.parent.parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
RUNTIME_DIR = PROJECT_ROOT / "_runtime"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# =============================================================================
# SECURE KEY MANAGER (Machine-Bound Encryption)
# =============================================================================
_secure_key_manager = None
_SECURE_KEY_AVAILABLE = False
try:
    from .utils.secure_key_manager import SecureKeyManager, is_key_encrypted
    _secure_key_manager = SecureKeyManager(str(PROJECT_ROOT))
    _SECURE_KEY_AVAILABLE = True
except ImportError:
    try:
        # Try relative import for running as script
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.utils.secure_key_manager import SecureKeyManager, is_key_encrypted
        _secure_key_manager = SecureKeyManager(str(PROJECT_ROOT))
        _SECURE_KEY_AVAILABLE = True
    except ImportError:
        pass

# Keys that should be encrypted when saved
ENCRYPTED_KEYS = {"GEMINI_API_KEY"}

# =============================================================================
# CONFIGURATION SCHEMA
# =============================================================================
CONFIG_SCHEMA = {
    "API Configuration": {
        "icon": "🔑",
        "variables": [
            {
                "key": "GEMINI_API_KEY",
                "type": "password",
                "default": "",
                "desc": "Your Gemini AI API Key",
                "tooltip": "Get your free key from: https://aistudio.google.com/",
            },
        ]
    },
    "Timing Settings": {
        "icon": "⏱️",
        "variables": [
            {
                "key": "INITIAL_WAIT",
                "type": "int",
                "default": 10,
                "min": 0,
                "max": 60,
                "desc": "Initial Wait (seconds)",
                "tooltip": "Seconds to wait before starting after launch",
            },
            {
                "key": "POST_ACTION_WAIT",
                "type": "int",
                "default": 10,
                "min": 0,
                "max": 60,
                "desc": "Post-Action Wait",
                "tooltip": "Seconds to wait after performing an action",
            },
            {
                "key": "SWITCH_QUESTION_WAIT",
                "type": "int",
                "default": 5,
                "min": 0,
                "max": 30,
                "desc": "Switch Question Wait",
                "tooltip": "Seconds to wait when switching between questions",
            },
            {
                "key": "POLL_INTERVAL",
                "type": "int",
                "default": 3,
                "min": 1,
                "max": 30,
                "desc": "Poll Interval",
                "tooltip": "Seconds between screen checks in Auto Mode",
            },
        ]
    },
    "API & Retry": {
        "icon": "🔄",
        "variables": [
            {
                "key": "MAX_RETRIES",
                "type": "int",
                "default": 2,
                "min": 0,
                "max": 10,
                "desc": "Max Retries",
                "tooltip": "Maximum number of retries for API calls on failure",
            },
        ]
    },
    "Mouse & Typing": {
        "icon": "⌨️",
        "variables": [
            {
                "key": "MOUSE_MOVE_DURATION",
                "type": "float",
                "default": 0.8,
                "min": 0.1,
                "max": 3.0,
                "step": 0.1,
                "desc": "Mouse Move Duration",
                "tooltip": "Duration of mouse movement animation (seconds)",
            },
            {
                "key": "TYPING_WPM_MIN",
                "type": "int",
                "default": 30,
                "min": 10,
                "max": 200,
                "desc": "Min Typing Speed (WPM)",
                "tooltip": "Minimum typing speed in Words Per Minute",
            },
            {
                "key": "TYPING_WPM_MAX",
                "type": "int",
                "default": 100,
                "min": 20,
                "max": 300,
                "desc": "Max Typing Speed (WPM)",
                "tooltip": "Maximum typing speed in Words Per Minute",
            },
        ]
    },
    "Feature Flags": {
        "icon": "🚀",
        "variables": [
            {
                "key": "HANDLE_DESCRIPTIVE_ANSWERS",
                "type": "bool",
                "default": True,
                "desc": "Handle Descriptive Answers",
                "tooltip": "Whether to handle descriptive/essay questions",
            },
            {
                "key": "ENABLE_DETAILED_MODE",
                "type": "bool",
                "default": True,
                "desc": "Enable Detailed Mode",
                "tooltip": "Enable handling of detailed/long answers with marks-based length",
            },
            {
                "key": "URGENT_MODE",
                "type": "bool",
                "default": False,
                "desc": "Urgent Mode",
                "tooltip": "Reduces delays for time-critical situations, faster typing",
            },
        ]
    },
    "Input Modes": {
        "icon": "🎮",
        "variables": [
            {
                "key": "MANUAL_MODE",
                "type": "bool",
                "default": False,
                "desc": "Manual Mode (Hotkeys Only)",
                "tooltip": "True = Hotkey-triggered, False = Automatic Loop",
            },
            {
                "key": "HOTKEY_MCQ",
                "type": "str",
                "default": "q",
                "desc": "MCQ Hotkey",
                "tooltip": "Hotkey to trigger MCQ detection (single key)",
            },
            {
                "key": "HOTKEY_DESCRIPTIVE",
                "type": "str",
                "default": "z",
                "desc": "Descriptive Hotkey",
                "tooltip": "Hotkey to trigger Descriptive question detection",
            },
            {
                "key": "HOTKEY_CLIPBOARD",
                "type": "str",
                "default": "c",
                "desc": "Clipboard Stream Hotkey",
                "tooltip": "Press 3x to stream clipboard content character-by-character",
            },
            {
                "key": "HOTKEY_MULTI_MCQ",
                "type": "str",
                "default": "m",
                "desc": "Multi-Select MCQ Hotkey",
                "tooltip": "Press 3x for checkbox questions with multiple correct answers",
            },
            {
                "key": "HOTKEY_LONG_MCQ",
                "type": "str",
                "default": "l",
                "desc": "Long/Scrolling MCQ Hotkey",
                "tooltip": "Press 3x for long questions that require scrolling multiple pages",
            },
            {
                "key": "HOTKEY_TOGGLE_MODE",
                "type": "str",
                "default": "t",
                "desc": "Toggle Mode Hotkey",
                "tooltip": "Press 3x to switch between Manual and Auto mode",
            },
            {
                "key": "HOTKEY_DELAY",
                "type": "float",
                "default": 2.0,
                "min": 0.5,
                "max": 10.0,
                "step": 0.5,
                "desc": "Hotkey Delay",
                "tooltip": "Delay in seconds after hotkey press before screen capture",
            },
        ]
    },
    "Developer Options": {
        "icon": "🛠️",
        "variables": [
            {
                "key": "DEVELOPER_MODE",
                "type": "bool",
                "default": False,
                "desc": "Developer Mode",
                "tooltip": "Show console window and extra logging",
            },
            {
                "key": "VERBOSE_STARTUP",
                "type": "bool",
                "default": False,
                "desc": "Verbose Startup",
                "tooltip": "Show detailed startup logs",
            },
            {
                "key": "DEV_MAX_ITERATIONS",
                "type": "int",
                "default": 2,
                "min": 1,
                "max": 100,
                "desc": "Dev Max Iterations",
                "tooltip": "Maximum loop iterations in developer mode",
            },
            {
                "key": "DEV_SAVE_SCREENSHOTS",
                "type": "bool",
                "default": True,
                "desc": "Save Screenshots",
                "tooltip": "Save screenshots to disk for debugging",
            },
        ]
    },
    "Auto-Update": {
        "icon": "📦",
        "variables": [
            {
                "key": "GITHUB_REPO_OWNER",
                "type": "str",
                "default": "your-username",
                "desc": "GitHub Repo Owner",
                "tooltip": "GitHub username/organization for update checks",
            },
            {
                "key": "GITHUB_REPO_NAME",
                "type": "str",
                "default": "scry",
                "desc": "GitHub Repo Name",
                "tooltip": "GitHub repository name for update checks",
            },
            {
                "key": "UPDATE_CHECK_INTERVAL_SECONDS",
                "type": "int",
                "default": 1800,
                "min": 0,
                "max": 86400,
                "desc": "Update Check Interval",
                "tooltip": "How often to check for updates (seconds). 0 = disabled",
            },
        ]
    },
}

# =============================================================================
# FLASK APP
# =============================================================================
app = Flask(__name__)
CORS(app)

# Global state for process management
app_process: Optional[subprocess.Popen] = None
test_process: Optional[subprocess.Popen] = None
app_output: List[str] = []
test_output: List[str] = []
app_running = False
test_running = False
output_lock = threading.Lock()

MAX_OUTPUT_LINES = 500


def load_env_values() -> Dict[str, str]:
    """
    Load current values from .env file.
    
    For encrypted keys (like GEMINI_API_KEY), returns a masked placeholder
    to indicate the key is set without exposing the encrypted value.
    """
    values = {}
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    key = k.strip()
                    val = v.strip()
                    
                    # For encrypted keys, show a masked value in the UI
                    if key in ENCRYPTED_KEYS and val and _SECURE_KEY_AVAILABLE:
                        if is_key_encrypted(val):
                            # Key is encrypted - show placeholder
                            values[key] = "••••••••••••••••"
                        else:
                            # Key is plain text - show it (will be encrypted on next save)
                            values[key] = val
                    else:
                        values[key] = val
    return values


def save_env_value(key: str, value: str) -> bool:
    """
    Save a single value to .env file.
    
    SECURITY: If the key is in ENCRYPTED_KEYS (like GEMINI_API_KEY),
    it will be encrypted using machine-bound encryption before saving.
    This ensures the key is useless if the project folder is copied.
    """
    try:
        if not ENV_PATH.exists():
            with open(ENV_PATH, "w", encoding="utf-8") as f:
                f.write("# Scry Configuration\n")
        
        value_to_save = value
        
        # Encrypt sensitive keys if secure key manager is available
        if key in ENCRYPTED_KEYS and value and _SECURE_KEY_AVAILABLE and _secure_key_manager:
            # Only encrypt if it's not already encrypted
            if not is_key_encrypted(value):
                try:
                    value_to_save = _secure_key_manager.encrypt_key(value)
                    print(f"[SECURITY] {key} encrypted with machine-bound encryption.")
                except Exception as e:
                    print(f"[WARNING] Could not encrypt {key}: {e}")
        
        # Use quote_mode="never" to prevent dotenv from wrapping values in quotes
        # This is critical for boolean values which should be True/False not 'True'/'False'
        set_key(str(ENV_PATH), key, value_to_save, quote_mode="never")
        return True
    except Exception as e:
        print(f"Error saving {key}: {e}")
        return False


def is_app_running() -> bool:
    """Check if the main app is running"""
    global app_process, app_running
    
    # Check our tracked process
    if app_process and app_process.poll() is None:
        return True
    
    # If process ended, update flag
    if app_process and app_process.poll() is not None:
        app_running = False
    
    return app_running


def stream_output(process: subprocess.Popen, output_list: List[str], prefix: str = ""):
    """Stream process output to the output list"""
    global app_running
    
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                timestamp = datetime.now().strftime("%H:%M:%S")
                formatted = f"[{timestamp}] {prefix}{line}"
                with output_lock:
                    output_list.append(formatted)
                    # Keep output bounded
                    while len(output_list) > MAX_OUTPUT_LINES:
                        output_list.pop(0)
        
        # Process ended
        exit_code = process.wait()
        with output_lock:
            output_list.append(f"\n[Process exited with code {exit_code}]\n")
    except Exception as e:
        with output_lock:
            output_list.append(f"\n[Error reading output: {e}]\n")
    finally:
        app_running = False


def ensure_environment_setup() -> tuple[bool, str]:
    """
    Ensure virtual environment exists and dependencies are installed.
    This makes the Start button a complete one-click solution for new machines.
    Returns (success, message).
    """
    global app_output
    
    venv_dir = RUNTIME_DIR / "venv"
    requirements_file = PROJECT_ROOT / "requirements.txt"
    
    # Step 1: Check if Python is available
    try:
        result = subprocess.run(
            ["python", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return False, "Python is not available in PATH"
        with output_lock:
            app_output.append(f"[SETUP] Found {result.stdout.strip()}\n")
    except Exception as e:
        return False, f"Python check failed: {str(e)}"
    
    # Step 2: Create virtual environment if it doesn't exist
    if not venv_dir.exists():
        with output_lock:
            app_output.append("[SETUP] Creating virtual environment...\n")
        try:
            result = subprocess.run(
                ["python", "-m", "venv", str(venv_dir)],
                capture_output=True, text=True, timeout=120,
                cwd=str(PROJECT_ROOT)
            )
            if result.returncode != 0:
                return False, f"Failed to create venv: {result.stderr}"
            with output_lock:
                app_output.append("[SETUP] Virtual environment created successfully\n")
        except subprocess.TimeoutExpired:
            return False, "Timeout creating virtual environment"
        except Exception as e:
            return False, f"Failed to create venv: {str(e)}"
    else:
        with output_lock:
            app_output.append("[SETUP] Using existing virtual environment\n")
    
    # Step 3: Determine the Python executable in the venv
    if sys.platform == "win32":
        venv_python = venv_dir / "Scripts" / "python.exe"
        venv_pip = venv_dir / "Scripts" / "pip.exe"
    else:
        venv_python = venv_dir / "bin" / "python"
        venv_pip = venv_dir / "bin" / "pip"
    
    if not venv_python.exists():
        return False, f"Virtual environment Python not found at {venv_python}"
    
    # Step 4: Install/upgrade pip
    with output_lock:
        app_output.append("[SETUP] Checking pip...\n")
    try:
        result = subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "-q"],
            capture_output=True, text=True, timeout=120,
            cwd=str(PROJECT_ROOT)
        )
        # We don't fail on pip upgrade issues, just log
        if result.returncode != 0:
            with output_lock:
                app_output.append(f"[WARN] pip upgrade issue: {result.stderr[:200]}\n")
    except Exception as e:
        with output_lock:
            app_output.append(f"[WARN] pip upgrade failed: {str(e)}\n")
    
    # Step 5: Install dependencies from requirements.txt
    if requirements_file.exists():
        with output_lock:
            app_output.append("[SETUP] Installing dependencies (this may take a while on first run)...\n")
        try:
            result = subprocess.run(
                [str(venv_python), "-m", "pip", "install", "-r", str(requirements_file), "-q"],
                capture_output=True, text=True, timeout=600,  # 10 min timeout for deps
                cwd=str(PROJECT_ROOT)
            )
            if result.returncode != 0:
                # Some packages might fail, log but continue
                with output_lock:
                    app_output.append(f"[WARN] Some dependencies may have issues: {result.stderr[:300]}\n")
            else:
                with output_lock:
                    app_output.append("[SETUP] Dependencies installed successfully\n")
        except subprocess.TimeoutExpired:
            with output_lock:
                app_output.append("[WARN] Dependency installation timed out - continuing anyway\n")
        except Exception as e:
            with output_lock:
                app_output.append(f"[WARN] Dependency installation issue: {str(e)}\n")
    else:
        with output_lock:
            app_output.append("[WARN] requirements.txt not found, skipping dependency install\n")
    
    # Step 6: Ensure .env file exists
    if not ENV_PATH.exists():
        with output_lock:
            app_output.append("[SETUP] Creating default .env configuration...\n")
        try:
            env_example = PROJECT_ROOT / ".env.example"
            if env_example.exists():
                import shutil
                shutil.copy(str(env_example), str(ENV_PATH))
                with output_lock:
                    app_output.append("[SETUP] Copied .env.example to .env\n")
            else:
                with open(ENV_PATH, 'w') as f:
                    f.write("# Scry Configuration\n")
                    f.write("# Add your GEMINI_API_KEY below:\n")
                    f.write("GEMINI_API_KEY=\n")
                with output_lock:
                    app_output.append("[SETUP] Created default .env file\n")
        except Exception as e:
            with output_lock:
                app_output.append(f"[WARN] Could not create .env: {str(e)}\n")
    
    with output_lock:
        app_output.append("[SETUP] Environment setup complete!\n")
    
    return True, "Environment ready"


def start_app() -> Dict[str, Any]:
    """Start the main application with output capture.
    Automatically sets up environment (venv, dependencies) on first run.
    """
    global app_process, app_output, app_running
    
    if is_app_running():
        return {"success": False, "message": "Application is already running"}
    
    # Clear previous output
    with output_lock:
        app_output = []
        app_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Initializing Scry...\n")
    
    # When running as frozen exe, we can't spawn subprocess with sys.executable
    # Instead, import and run main directly in a thread
    if IS_FROZEN:
        try:
            from src.main import main as scry_main
            
            def run_scry_main():
                global app_running
                try:
                    with output_lock:
                        app_output.append("[INFO] Running Scry in embedded mode...\n")
                    scry_main()
                except Exception as e:
                    with output_lock:
                        app_output.append(f"[ERROR] {str(e)}\n")
                finally:
                    app_running = False
            
            thread = threading.Thread(target=run_scry_main, daemon=True)
            thread.start()
            app_running = True
            return {"success": True, "message": "Application started (embedded mode)"}
        except Exception as e:
            with output_lock:
                app_output.append(f"[ERROR] Failed to start: {str(e)}\n")
            return {"success": False, "message": str(e)}
    
    # ========================================================================
    # AUTO-SETUP: Ensure environment is ready before starting
    # This makes the Start button work on a fresh machine with just Python
    # ========================================================================
    setup_success, setup_message = ensure_environment_setup()
    if not setup_success:
        with output_lock:
            app_output.append(f"[ERROR] Setup failed: {setup_message}\n")
        return {"success": False, "message": f"Setup failed: {setup_message}"}
    
    try:
        # Determine venv Python path
        venv_dir = RUNTIME_DIR / "venv"
        if sys.platform == "win32":
            venv_python = venv_dir / "Scripts" / "python.exe"
        else:
            venv_python = venv_dir / "bin" / "python"
        
        # Use venv Python if it exists, otherwise fall back to system Python
        python_exe = str(venv_python) if venv_python.exists() else sys.executable
        
        with output_lock:
            app_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting Scry application...\n")
        
        # Setup environment
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"  # Force unbuffered output
        
        # Ensure runtime directories exist
        RUNTIME_DIR.mkdir(exist_ok=True)
        (RUNTIME_DIR / "logs").mkdir(exist_ok=True)
        
        # Run directly with Python for output capture
        app_process = subprocess.Popen(
            [python_exe, "-u", "-m", "src.main"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        
        app_running = True
        
        # Start output streaming in background
        thread = threading.Thread(target=stream_output, args=(app_process, app_output, ""))
        thread.daemon = True
        thread.start()
        
        return {"success": True, "message": "Application started"}
    except Exception as e:
        with output_lock:
            app_output.append(f"[ERROR] Failed to start: {str(e)}\n")
        return {"success": False, "message": str(e)}


def stop_app() -> Dict[str, Any]:
    """Stop the main application"""
    global app_process, app_running
    
    try:
        if app_process:
            # Try graceful termination first
            app_process.terminate()
            try:
                app_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                app_process.kill()
        
        # Also kill any lingering processes
        if sys.platform == "win32":
            subprocess.run(
                ["wmic", "process", "where", 
                 "CommandLine like '%src.main%' and name like 'python%'",
                 "call", "terminate"],
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
        
        app_process = None
        app_running = False
        
        with output_lock:
            app_output.append(f"\n[{datetime.now().strftime('%H:%M:%S')}] Application stopped.\n")
        
        return {"success": True, "message": "Application stopped"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def run_tests_async():
    """Run tests in background thread"""
    global test_output, test_running
    
    with output_lock:
        test_output = []
        test_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting test suite...\n\n")
    test_running = True
    
    # Tests require subprocess with Python, not available when frozen
    if IS_FROZEN:
        with output_lock:
            test_output.append("[WARN] Tests are not available when running from the compiled executable.\n")
            test_output.append("[INFO] Please run tests from source using: python -m pytest tests/\n")
        test_running = False
        return
    
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    try:
        # Run pytest
        with output_lock:
            test_output.append("=== Running Unit Tests ===\n")
        
        result = subprocess.run(
            [sys.executable, "-u", "-m", "pytest", "tests/", "-v", "--tb=short"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            env=env
        )
        with output_lock:
            test_output.append(result.stdout)
            if result.returncode != 0:
                test_output.append(f"\n[WARN] Unit tests had failures\n{result.stderr}\n")
            else:
                test_output.append("\n[OK] Unit tests passed!\n")
        
        # Run human typing test
        with output_lock:
            test_output.append("\n=== Human Typing Validation ===\n")
        
        typing_test = PROJECT_ROOT / "tests" / "test_human_typing.py"
        if typing_test.exists():
            result = subprocess.run(
                [sys.executable, "-u", str(typing_test)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=60,
                env=env
            )
            with output_lock:
                test_output.append(result.stdout)
                if result.returncode == 0:
                    test_output.append("[OK] Human typing validation passed!\n")
                else:
                    test_output.append(f"[WARN] Typing test issues: {result.stderr}\n")
        
        # Validate environment
        with output_lock:
            test_output.append("\n=== Environment Validation ===\n")
        
        validate_script = PROJECT_ROOT / "src" / "validate_env.py"
        if validate_script.exists():
            result = subprocess.run(
                [sys.executable, "-u", str(validate_script)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            with output_lock:
                test_output.append(result.stdout)
                if result.returncode == 0:
                    test_output.append("[OK] Environment validation passed!\n")
                else:
                    test_output.append(f"[WARN] Environment issues: {result.stderr}\n")
        
        with output_lock:
            test_output.append(f"\n[{datetime.now().strftime('%H:%M:%S')}] Test suite completed!\n")
        
    except subprocess.TimeoutExpired:
        with output_lock:
            test_output.append("[ERROR] Test timed out!\n")
    except Exception as e:
        with output_lock:
            test_output.append(f"[ERROR] Test error: {str(e)}\n")
    finally:
        test_running = False


# =============================================================================
# HTML TEMPLATE - MODERN UI WITH TERMINAL
# =============================================================================
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scry Control Panel</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a24;
            --bg-card-hover: #222232;
            --bg-input: #0f0f17;
            --bg-terminal: #0c0c10;
            
            --accent: #6366f1;
            --accent-hover: #818cf8;
            --accent-glow: rgba(99, 102, 241, 0.3);
            
            --success: #22c55e;
            --success-glow: rgba(34, 197, 94, 0.3);
            --warning: #f59e0b;
            --error: #ef4444;
            --error-glow: rgba(239, 68, 68, 0.3);
            
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --text-terminal: #22d3ee;
            
            --border: #2a2a3a;
            --border-focus: #6366f1;
            
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 16px;
            
            --shadow-md: 0 4px 20px rgba(0,0,0,0.4);
            --shadow-glow: 0 0 40px var(--accent-glow);
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }
        
        .bg-gradient {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: 
                radial-gradient(ellipse at 20% 20%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 80%, rgba(139, 92, 246, 0.06) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }
        
        .app-container {
            display: grid;
            grid-template-columns: 1fr 420px;
            grid-template-rows: auto 1fr;
            min-height: 100vh;
            gap: 0;
            position: relative;
            z-index: 1;
        }
        
        /* Header */
        .header {
            grid-column: 1 / -1;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 24px;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
        }
        
        .header-left {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        
        .logo { font-size: 32px; }
        
        .header h1 {
            font-size: 20px;
            font-weight: 600;
            background: linear-gradient(135deg, #fff 0%, #a5b4fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .header-right {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .status-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            font-size: 13px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        .status-dot.running { background: var(--success); box-shadow: 0 0 10px var(--success-glow); }
        .status-dot.stopped { background: var(--text-muted); animation: none; }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* Main Content */
        .main-content {
            padding: 24px;
            overflow-y: auto;
            max-height: calc(100vh - 70px);
        }
        
        /* Control Bar */
        .control-bar {
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
        }
        
        .control-btn {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            padding: 14px 20px;
            border: none;
            border-radius: var(--radius-md);
            font-family: inherit;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .control-btn.start {
            background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
            color: white;
        }
        
        .control-btn.stop {
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
        }
        
        .control-btn.test {
            background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
            color: white;
        }
        
        .control-btn:hover { transform: translateY(-2px); }
        .control-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        
        /* Sections */
        .section {
            background: var(--bg-card);
            border-radius: var(--radius-lg);
            border: 1px solid var(--border);
            margin-bottom: 16px;
            overflow: hidden;
        }
        
        .section-header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 14px 18px;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            user-select: none;
        }
        
        .section-header:hover { background: var(--bg-card-hover); }
        
        .section-icon { font-size: 18px; }
        .section-title { font-size: 14px; font-weight: 600; flex: 1; }
        .section-toggle { color: var(--text-muted); transition: transform 0.2s; }
        .section.collapsed .section-toggle { transform: rotate(-90deg); }
        .section.collapsed .section-content { display: none; }
        
        .section-content { padding: 16px 18px; }
        
        /* Config Items */
        .config-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
        }
        
        .config-item:last-child { border-bottom: none; }
        
        .config-info { flex: 1; }
        .config-label { font-size: 13px; font-weight: 500; }
        .config-tooltip { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
        
        .config-control { min-width: 140px; text-align: right; }
        
        /* Toggle Switch */
        .toggle {
            position: relative;
            width: 44px;
            height: 24px;
            display: inline-block;
        }
        
        .toggle input { opacity: 0; width: 0; height: 0; }
        
        .toggle-slider {
            position: absolute;
            cursor: pointer;
            inset: 0;
            background: var(--bg-input);
            border-radius: 24px;
            transition: all 0.3s;
            border: 2px solid var(--border);
        }
        
        .toggle-slider::before {
            content: "";
            position: absolute;
            height: 16px;
            width: 16px;
            left: 2px;
            bottom: 2px;
            background: white;
            border-radius: 50%;
            transition: all 0.3s;
        }
        
        .toggle input:checked + .toggle-slider {
            background: var(--success);
            border-color: var(--success);
        }
        
        .toggle input:checked + .toggle-slider::before {
            transform: translateX(20px);
        }
        
        /* Inputs */
        .input-field {
            width: 100%;
            max-width: 140px;
            padding: 8px 12px;
            background: var(--bg-input);
            border: 2px solid var(--border);
            border-radius: var(--radius-sm);
            color: var(--text-primary);
            font-family: inherit;
            font-size: 13px;
        }
        
        .input-field:focus {
            outline: none;
            border-color: var(--accent);
        }
        
        /* Number input */
        .number-input {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .number-btn {
            width: 28px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--bg-input);
            border: 2px solid var(--border);
            border-radius: var(--radius-sm);
            color: var(--text-primary);
            font-size: 16px;
            cursor: pointer;
        }
        
        .number-btn:hover {
            background: var(--accent);
            border-color: var(--accent);
        }
        
        .number-value {
            width: 60px;
            text-align: center;
            padding: 6px 8px;
            background: var(--bg-input);
            border: 2px solid var(--border);
            border-radius: var(--radius-sm);
            color: var(--text-primary);
            font-size: 13px;
        }
        
        /* Terminal Panel */
        .terminal-panel {
            background: var(--bg-terminal);
            border-left: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            max-height: calc(100vh - 70px);
        }
        
        .terminal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
        }
        
        .terminal-title {
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .terminal-tabs {
            display: flex;
            gap: 4px;
        }
        
        .terminal-tab {
            padding: 6px 12px;
            background: transparent;
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            color: var(--text-muted);
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .terminal-tab.active {
            background: var(--accent);
            border-color: var(--accent);
            color: white;
        }
        
        .terminal-content {
            flex: 1;
            padding: 16px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            line-height: 1.7;
            white-space: pre-wrap;
            word-break: break-all;
            color: var(--text-terminal);
        }
        
        .terminal-content::-webkit-scrollbar { width: 8px; }
        .terminal-content::-webkit-scrollbar-track { background: var(--bg-primary); }
        .terminal-content::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
        
        .terminal-content .error { color: var(--error); }
        .terminal-content .success { color: var(--success); }
        .terminal-content .warning { color: var(--warning); }
        
        .terminal-empty {
            color: var(--text-muted);
            font-style: italic;
        }
        
        .terminal-actions {
            padding: 12px 16px;
            border-top: 1px solid var(--border);
            display: flex;
            gap: 8px;
        }
        
        .terminal-btn {
            padding: 8px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            color: var(--text-secondary);
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .terminal-btn:hover {
            background: var(--bg-card-hover);
            color: var(--text-primary);
        }
        
        /* Toast */
        .toast {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            padding: 12px 24px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-md);
            display: flex;
            align-items: center;
            gap: 10px;
            transition: transform 0.3s ease;
            z-index: 1000;
        }
        
        .toast.show { transform: translateX(-50%) translateY(0); }
        .toast.success { border-color: var(--success); }
        .toast.error { border-color: var(--error); }
        
        /* Spinner */
        .spinner {
            width: 16px;
            height: 16px;
            border: 2px solid transparent;
            border-top-color: currentColor;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin { to { transform: rotate(360deg); } }
        
        /* Responsive */
        @media (max-width: 900px) {
            .app-container {
                grid-template-columns: 1fr;
                grid-template-rows: auto auto 1fr;
            }
            
            .terminal-panel {
                border-left: none;
                border-top: 1px solid var(--border);
                max-height: 300px;
            }
        }
    </style>
</head>
<body>
    <div class="bg-gradient"></div>
    
    <div class="app-container">
        <!-- Header -->
        <header class="header">
            <div class="header-left">
                <span class="logo">🔮</span>
                <h1>Scry Control Panel</h1>
            </div>
            <div class="header-right">
                <div class="status-badge">
                    <div class="status-dot" id="statusDot"></div>
                    <span id="statusText">Checking...</span>
                </div>
            </div>
        </header>
        
        <!-- Main Content -->
        <main class="main-content">
            <!-- Control Bar -->
            <div class="control-bar">
                <button class="control-btn start" id="startBtn" onclick="startApp()">
                    ▶ Start
                </button>
                <button class="control-btn stop" id="stopBtn" onclick="stopApp()">
                    ◼ Stop
                </button>
                <button class="control-btn test" id="testBtn" onclick="runTests()">
                    🧪 Test
                </button>
            </div>
            
            <!-- Config Sections -->
            <div id="configSections"></div>
        </main>
        
        <!-- Terminal Panel -->
        <aside class="terminal-panel">
            <div class="terminal-header">
                <span class="terminal-title">📺 Output</span>
                <div class="terminal-tabs">
                    <button class="terminal-tab active" id="tabApp" onclick="switchTab('app')">App</button>
                    <button class="terminal-tab" id="tabTest" onclick="switchTab('test')">Tests</button>
                </div>
            </div>
            <div class="terminal-content" id="terminalContent">
                <span class="terminal-empty">No output yet. Start the application to see logs.</span>
            </div>
            <div class="terminal-actions">
                <button class="terminal-btn" onclick="clearTerminal()">Clear</button>
                <button class="terminal-btn" onclick="copyTerminal()">Copy</button>
            </div>
        </aside>
    </div>
    
    <!-- Toast -->
    <div class="toast" id="toast">
        <span id="toastIcon">✓</span>
        <span id="toastMessage">Saved</span>
    </div>
    
    <script>
        const configSchema = ''' + json.dumps(CONFIG_SCHEMA) + ''';
        let currentTab = 'app';
        let autoScroll = true;
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            renderSections();
            loadValues();
            checkStatus();
            setInterval(checkStatus, 2000);
            setInterval(updateTerminal, 1000);
        });
        
        function renderSections() {
            const container = document.getElementById('configSections');
            container.innerHTML = '';
            
            for (const [name, section] of Object.entries(configSchema)) {
                const el = document.createElement('div');
                el.className = 'section';
                el.innerHTML = `
                    <div class="section-header" onclick="this.parentElement.classList.toggle('collapsed')">
                        <span class="section-icon">${section.icon}</span>
                        <span class="section-title">${name}</span>
                        <span class="section-toggle">▼</span>
                    </div>
                    <div class="section-content">
                        ${section.variables.map(v => renderConfigItem(v)).join('')}
                    </div>
                `;
                container.appendChild(el);
            }
        }
        
        function renderConfigItem(config) {
            const { key, type, desc, tooltip } = config;
            let control = '';
            
            if (type === 'bool') {
                control = `<label class="toggle"><input type="checkbox" id="${key}" onchange="saveValue('${key}', this.checked)"><span class="toggle-slider"></span></label>`;
            } else if (type === 'int' || type === 'float') {
                const step = config.step || (type === 'float' ? 0.1 : 1);
                control = `
                    <div class="number-input">
                        <button class="number-btn" onclick="adjustNumber('${key}', -${step})">-</button>
                        <input type="number" class="number-value" id="${key}" value="${config.default}" step="${step}" min="${config.min || 0}" max="${config.max || 9999}" onchange="saveValue('${key}', this.value)">
                        <button class="number-btn" onclick="adjustNumber('${key}', ${step})">+</button>
                    </div>`;
            } else if (type === 'password') {
                control = `<input type="password" class="input-field" id="${key}" placeholder="••••••••" onchange="saveValue('${key}', this.value)">`;
            } else {
                control = `<input type="text" class="input-field" id="${key}" placeholder="Enter..." onchange="saveValue('${key}', this.value)">`;
            }
            
            return `
                <div class="config-item">
                    <div class="config-info">
                        <div class="config-label">${desc}</div>
                        <div class="config-tooltip">${tooltip}</div>
                    </div>
                    <div class="config-control">${control}</div>
                </div>`;
        }
        
        async function loadValues() {
            try {
                const res = await fetch('/api/config');
                const values = await res.json();
                for (const [key, val] of Object.entries(values)) {
                    const el = document.getElementById(key);
                    if (el) {
                        if (el.type === 'checkbox') {
                            el.checked = val === 'True' || val === 'true' || val === true;
                        } else {
                            el.value = val;
                        }
                    }
                }
            } catch (e) { console.error(e); }
        }
        
        async function saveValue(key, value) {
            if (typeof value === 'boolean') value = value ? 'True' : 'False';
            try {
                const res = await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ key, value: String(value) })
                });
                if (res.ok) showToast('Saved!', 'success');
            } catch (e) { showToast('Save failed', 'error'); }
        }
        
        function adjustNumber(key, delta) {
            const el = document.getElementById(key);
            if (el) {
                let val = parseFloat(el.value) + delta;
                val = Math.max(parseFloat(el.min), Math.min(parseFloat(el.max), val));
                el.value = Math.round(val * 100) / 100;
                saveValue(key, el.value);
            }
        }
        
        async function checkStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                const dot = document.getElementById('statusDot');
                const text = document.getElementById('statusText');
                
                if (data.running) {
                    dot.className = 'status-dot running';
                    text.textContent = 'Running';
                } else {
                    dot.className = 'status-dot stopped';
                    text.textContent = 'Stopped';
                }
            } catch (e) { }
        }
        
        async function updateTerminal() {
            try {
                const res = await fetch('/api/output?tab=' + currentTab);
                const data = await res.json();
                const content = document.getElementById('terminalContent');
                
                if (data.output && data.output.length > 0) {
                    content.innerHTML = escapeHtml(data.output);
                    if (autoScroll) {
                        content.scrollTop = content.scrollHeight;
                    }
                }
            } catch (e) { }
        }
        
        function escapeHtml(text) {
            return text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/\\[ERROR\\]/g, '<span class="error">[ERROR]</span>')
                .replace(/\\[OK\\]/g, '<span class="success">[OK]</span>')
                .replace(/\\[WARN\\]/g, '<span class="warning">[WARN]</span>');
        }
        
        function switchTab(tab) {
            currentTab = tab;
            document.getElementById('tabApp').className = tab === 'app' ? 'terminal-tab active' : 'terminal-tab';
            document.getElementById('tabTest').className = tab === 'test' ? 'terminal-tab active' : 'terminal-tab';
            updateTerminal();
        }
        
        function clearTerminal() {
            document.getElementById('terminalContent').innerHTML = '<span class="terminal-empty">Terminal cleared.</span>';
            fetch('/api/clear?tab=' + currentTab, { method: 'POST' });
        }
        
        function copyTerminal() {
            const content = document.getElementById('terminalContent').innerText;
            navigator.clipboard.writeText(content);
            showToast('Copied to clipboard', 'success');
        }
        
        async function startApp() {
            const btn = document.getElementById('startBtn');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Starting...';
            switchTab('app');
            
            try {
                const res = await fetch('/api/start', { method: 'POST' });
                const data = await res.json();
                showToast(data.success ? 'Started!' : data.message, data.success ? 'success' : 'error');
            } catch (e) { showToast('Failed to start', 'error'); }
            
            btn.disabled = false;
            btn.innerHTML = '▶ Start';
            checkStatus();
        }
        
        async function stopApp() {
            const btn = document.getElementById('stopBtn');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Stopping...';
            
            try {
                const res = await fetch('/api/stop', { method: 'POST' });
                const data = await res.json();
                showToast(data.success ? 'Stopped' : data.message, data.success ? 'success' : 'error');
            } catch (e) { showToast('Failed to stop', 'error'); }
            
            btn.disabled = false;
            btn.innerHTML = '◼ Stop';
            checkStatus();
        }
        
        async function runTests() {
            const btn = document.getElementById('testBtn');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Testing...';
            switchTab('test');
            
            try {
                await fetch('/api/test', { method: 'POST' });
                
                const poll = setInterval(async () => {
                    const res = await fetch('/api/status');
                    const data = await res.json();
                    if (!data.test_running) {
                        clearInterval(poll);
                        btn.disabled = false;
                        btn.innerHTML = '🧪 Test';
                        showToast('Tests completed!', 'success');
                    }
                }, 1000);
            } catch (e) {
                showToast('Failed to run tests', 'error');
                btn.disabled = false;
                btn.innerHTML = '🧪 Test';
            }
        }
        
        function showToast(message, type = 'success') {
            const toast = document.getElementById('toast');
            document.getElementById('toastIcon').textContent = type === 'success' ? '✓' : '✗';
            document.getElementById('toastMessage').textContent = message;
            toast.className = `toast ${type} show`;
            setTimeout(() => toast.classList.remove('show'), 3000);
        }
    </script>
</body>
</html>
'''


# =============================================================================
# API ROUTES
# =============================================================================
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(load_env_values())


@app.route('/api/config', methods=['POST'])
def set_config():
    data = request.json
    key = data.get('key')
    value = data.get('value')
    if not key:
        return jsonify({"error": "Key required"}), 400
    if save_env_value(key, value):
        return jsonify({"success": True})
    return jsonify({"error": "Failed to save"}), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "running": is_app_running(),
        "test_running": test_running
    })


@app.route('/api/output', methods=['GET'])
def get_output():
    tab = request.args.get('tab', 'app')
    with output_lock:
        if tab == 'test':
            output = "".join(test_output)
        else:
            output = "".join(app_output)
    return jsonify({"output": output})


@app.route('/api/clear', methods=['POST'])
def clear_output():
    global app_output, test_output
    tab = request.args.get('tab', 'app')
    with output_lock:
        if tab == 'test':
            test_output = []
        else:
            app_output = []
    return jsonify({"success": True})


@app.route('/api/start', methods=['POST'])
def api_start():
    return jsonify(start_app())


@app.route('/api/stop', methods=['POST'])
def api_stop():
    return jsonify(stop_app())


@app.route('/api/test', methods=['POST'])
def api_test():
    global test_running
    if test_running:
        return jsonify({"success": False, "message": "Tests already running"})
    thread = threading.Thread(target=run_tests_async)
    thread.daemon = True
    thread.start()
    return jsonify({"success": True, "message": "Tests started"})


def main():
    import webbrowser
    
    port = 5000
    url = f"http://localhost:{port}"
    
    print(f"""
============================================================
  SCRY CONTROL PANEL
============================================================
  Web interface: {url}
  Press Ctrl+C to stop
============================================================
""")
    
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)


if __name__ == '__main__':
    main()
