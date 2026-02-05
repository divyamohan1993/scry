"""
Configuration settings for Scry

All settings are loaded from environment variables (.env file).
See .env.example for all available options.

SECURITY: API keys are encrypted using machine-bound encryption.
Copying the project folder will invalidate stored API keys.
"""

import os
import sys

from dotenv import load_dotenv

# =============================================================================
# DETECT IF RUNNING AS FROZEN EXE (PyInstaller)
# =============================================================================
IS_FROZEN = getattr(sys, 'frozen', False)

# Determine base directory (for EXE vs script)
if IS_FROZEN:
    # Running as compiled EXE
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running as script
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file (located next to EXE or in project root)
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

# =============================================================================
# SECURE KEY MANAGER INITIALIZATION
# =============================================================================
# Import secure key manager for encrypted API key handling
try:
    from .utils.secure_key_manager import SecureKeyManager, is_key_encrypted
    _secure_key_manager = SecureKeyManager(BASE_DIR)
    _SECURE_KEY_AVAILABLE = True
except ImportError:
    _secure_key_manager = None
    _SECURE_KEY_AVAILABLE = False
    print("[WARNING] SecureKeyManager not available. API keys will be stored in plain text.")


def get_bool_env(key, default=False):
    """Helper to parse boolean env vars case-insensitively."""
    val = os.getenv(key, str(default)).lower()
    return val in ("true", "1", "yes", "on")


def get_float_env(key, default=0.0):
    try:
        return float(os.getenv(key, default))
    except ValueError:
        return default


def get_int_env(key, default=0):
    try:
        return int(os.getenv(key, default))
    except ValueError:
        return default


def _prompt_for_api_key():
    """
    Prompt user for API key using a GUI dialog (for EXE mode).
    This ensures the key is never hardcoded and users must provide their own.
    """
    try:
        import tkinter as tk
        from tkinter import simpledialog, messagebox
        
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.attributes('-topmost', True)  # Bring dialog to front
        
        messagebox.showinfo(
            "API Key Required",
            "Welcome to Scry!\n\n"
            "You need to provide your Gemini API Key to use this application.\n"
            "Get your free key from: https://aistudio.google.com/\n\n"
            "Your key will be saved locally in a .env file next to this application."
        )
        
        api_key = simpledialog.askstring(
            "Enter Gemini API Key",
            "Paste your Gemini API Key:",
            parent=root
        )
        
        root.destroy()
        
        if api_key and api_key.strip():
            return api_key.strip()
        return None
        
    except Exception:
        # Fallback to console input if tkinter fails
        print("\n" + "=" * 60)
        print("API KEY REQUIRED")
        print("=" * 60)
        print("Get your free Gemini API key from: https://aistudio.google.com/")
        print("=" * 60)
        api_key = input("Enter your Gemini API Key: ").strip()
        return api_key if api_key else None


def _save_api_key_to_env(api_key):
    """
    Save the API key to the .env file.
    
    SECURITY: The API key is encrypted using machine-bound encryption
    before being saved. This ensures:
    1. The key is not stored in plain text
    2. Copying the project folder invalidates the key
    """
    # Encrypt the API key if secure key manager is available
    key_to_save = api_key
    if _SECURE_KEY_AVAILABLE and _secure_key_manager:
        try:
            key_to_save = _secure_key_manager.encrypt_key(api_key)
            print("[SECURITY] API key encrypted with machine-bound encryption.")
        except Exception as e:
            print(f"[WARNING] Could not encrypt API key: {e}. Saving in plain text.")
    
    env_content = f"""# Scry Configuration
# Generated automatically - DO NOT SHARE THIS FILE
# SECURITY: API key is encrypted and bound to this machine.
# Copying this file to another location will invalidate the key.

GEMINI_API_KEY={key_to_save}

# Default settings (modify as needed)
DEVELOPER_MODE=False
VERBOSE_STARTUP=False
"""
    try:
        with open(ENV_PATH, 'w', encoding='utf-8') as f:
            f.write(env_content)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save .env file: {e}")
        return False

# =============================================================================
# API CONFIGURATION (with Secure Key Decryption)
# =============================================================================
_raw_api_key = os.getenv("GEMINI_API_KEY")
GEMINI_API_KEY = None
_key_needs_reentry = False

# Handle encrypted or plain API key
if _raw_api_key and _raw_api_key != "YOUR_GEMINI_API_KEY_HERE":
    if _SECURE_KEY_AVAILABLE and _secure_key_manager and is_key_encrypted(_raw_api_key):
        # Key is encrypted - try to decrypt it
        decrypted = _secure_key_manager.decrypt_key(_raw_api_key)
        if decrypted:
            GEMINI_API_KEY = decrypted
        else:
            # Decryption failed - key is invalid for this machine/path
            print("[SECURITY] Encrypted API key is invalid for this installation.")
            print("[SECURITY] This can happen if the project folder was copied or moved.")
            _key_needs_reentry = True
    elif _SECURE_KEY_AVAILABLE and _secure_key_manager and not is_key_encrypted(_raw_api_key):
        # Plain text key found - migrate it to encrypted format
        print("[SECURITY] Migrating plain-text API key to encrypted format...")
        encrypted = _secure_key_manager.encrypt_key(_raw_api_key)
        
        # Update the .env file with encrypted key
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            with open(ENV_PATH, "w", encoding="utf-8") as f:
                for line in lines:
                    if line.strip().startswith("GEMINI_API_KEY="):
                        f.write(f"GEMINI_API_KEY={encrypted}\n")
                    else:
                        f.write(line)
            print("[SECURITY] API key successfully encrypted and saved.")
        except Exception as e:
            print(f"[WARNING] Could not migrate API key to encrypted format: {e}")
        
        # Use the plain key for this session
        GEMINI_API_KEY = _raw_api_key
    else:
        # No secure key manager available - use plain key
        GEMINI_API_KEY = _raw_api_key

# Check if API key is missing, placeholder, or needs re-entry
if not GEMINI_API_KEY or _key_needs_reentry:
    if IS_FROZEN:
        # Running as EXE - prompt user for API key
        if _key_needs_reentry:
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showwarning(
                    "API Key Invalid",
                    "Your API key is no longer valid for this installation.\n\n"
                    "This happens when the project folder is copied or moved.\n"
                    "Please re-enter your API key."
                )
                root.destroy()
            except Exception:
                print("[SECURITY] API key invalid. Please re-enter.")
        
        GEMINI_API_KEY = _prompt_for_api_key()
        
        if GEMINI_API_KEY:
            # Save to .env for future runs (will be encrypted)
            if _save_api_key_to_env(GEMINI_API_KEY):
                os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
            else:
                # Still usable for this session even if save fails
                os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
        else:
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror(
                    "API Key Required",
                    "Cannot run without a valid Gemini API Key.\n"
                    "The application will now exit."
                )
                root.destroy()
            except Exception:
                print("[ERROR] Cannot run without a valid Gemini API Key.")
            sys.exit(1)
    else:
        # Running as script - raise error (use validate_env.py flow)
        error_msg = "GEMINI_API_KEY is not set or is still a placeholder. "
        if _key_needs_reentry:
            error_msg = (
                "GEMINI_API_KEY decryption failed. The project may have been copied or moved. "
                "Please re-enter your API key in the .env file or delete the encrypted value."
            )
        raise ValueError(error_msg + "Please set a valid key in your .env file.")

# =============================================================================
# PATHS (BASE_DIR already defined at top based on frozen/script mode)
# =============================================================================
RUNTIME_DIR = os.path.join(BASE_DIR, "_runtime")
LOGS_DIR = os.path.join(RUNTIME_DIR, "logs")
SCREENSHOTS_DIR = os.path.join(RUNTIME_DIR, "screenshots")
DEBUG_DIR = os.path.join(RUNTIME_DIR, "debug")

# Create directories if they don't exist
for directory in [LOGS_DIR, SCREENSHOTS_DIR, DEBUG_DIR]:
    os.makedirs(directory, exist_ok=True)

# =============================================================================
# TIMING CONFIGURATION (all values in seconds)
# =============================================================================
INITIAL_WAIT = get_int_env("INITIAL_WAIT", 10)
POST_ACTION_WAIT = get_int_env("POST_ACTION_WAIT", 10)
SWITCH_QUESTION_WAIT = get_int_env("SWITCH_QUESTION_WAIT", 5)
POLL_INTERVAL = get_int_env("POLL_INTERVAL", 3)

# =============================================================================
# RETRY CONFIGURATION
# =============================================================================
MAX_RETRIES = get_int_env("MAX_RETRIES", 2)

# =============================================================================
# MOUSE MOVEMENT CONFIGURATION
# =============================================================================
MOUSE_MOVE_DURATION = get_float_env("MOUSE_MOVE_DURATION", 0.8)

# =============================================================================
# FEATURE FLAGS
# =============================================================================
HANDLE_DESCRIPTIVE_ANSWERS = get_bool_env("HANDLE_DESCRIPTIVE_ANSWERS", True)
ENABLE_DETAILED_MODE = get_bool_env("ENABLE_DETAILED_MODE", True)
TYPING_WPM_MIN = get_int_env("TYPING_WPM_MIN", 30)
TYPING_WPM_MAX = get_int_env("TYPING_WPM_MAX", 100)

# SECURITY: Force production mode when running as compiled EXE
# This prevents debug info from being exposed in distributed builds
if IS_FROZEN:
    DEVELOPER_MODE = False
    VERBOSE_STARTUP = False
else:
    DEVELOPER_MODE = get_bool_env("DEVELOPER_MODE", False)
    VERBOSE_STARTUP = get_bool_env("VERBOSE_STARTUP", False)

# Developer mode specific settings (only used when not frozen)
DEV_MAX_ITERATIONS = get_int_env("DEV_MAX_ITERATIONS", 2)
DEV_SAVE_SCREENSHOTS = get_bool_env("DEV_SAVE_SCREENSHOTS", True) if not IS_FROZEN else False

# =============================================================================
# INPUT MODES
# =============================================================================
MANUAL_MODE = get_bool_env("MANUAL_MODE", False)
HOTKEY_MCQ = os.getenv("HOTKEY_MCQ", "q")
HOTKEY_DESCRIPTIVE = os.getenv("HOTKEY_DESCRIPTIVE", "z")
HOTKEY_CLIPBOARD = os.getenv("HOTKEY_CLIPBOARD", "c")
HOTKEY_MULTI_MCQ = os.getenv("HOTKEY_MULTI_MCQ", "m")
HOTKEY_DELAY = get_float_env("HOTKEY_DELAY", 2.0)
URGENT_MODE = get_bool_env("URGENT_MODE", False)

# =============================================================================
# UPDATE CONFIGURATION
# =============================================================================
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER", "divyamohan1993")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME", "scry")
# URL to check for the latest version file (raw content)
VERSION_CHECK_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/main/src/version.py"
# URL to download the latest executable (Release asset)
LATEST_RELEASE_URL = f"https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest/download/Scry.exe"

UPDATE_CHECK_INTERVAL_SECONDS = get_int_env("UPDATE_CHECK_INTERVAL_SECONDS", 300)

# =============================================================================
# LICENSING CONFIGURATION
# =============================================================================
# When enabled, requires a one-time license key on each run
# Only the owner (with the private key) can generate valid keys
REQUIRE_LICENSE = get_bool_env("REQUIRE_LICENSE", False)

# License validation happens on startup
_LICENSE_VALIDATED = False

def validate_license() -> bool:
    """
    Validate the session license if licensing is enabled.
    
    Returns:
        True if license is valid or licensing is disabled
    """
    global _LICENSE_VALIDATED
    
    if not REQUIRE_LICENSE:
        return True
    
    if _LICENSE_VALIDATED:
        return True
    
    try:
        from .utils.license_manager import require_license
        _LICENSE_VALIDATED = require_license(BASE_DIR, use_gui=True)
        return _LICENSE_VALIDATED
    except ImportError as e:
        print(f"[LICENSE] License module not available: {e}")
        return False
    except Exception as e:
        print(f"[LICENSE] Error validating license: {e}")
        return False
