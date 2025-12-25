"""
Environment validation script for Scry.

This script ensures the .env file exists and contains valid values
for all required configuration variables. It prompts the user
interactively if any values are missing or still contain placeholders.

SECURITY: API keys are automatically encrypted using machine-bound 
encryption when saved.
"""

import os
import shutil
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ENV_PATH = ".env"
EXAMPLE_PATH = ".env.example"

# Try to import secure key manager
_secure_key_manager = None
_SECURE_KEY_AVAILABLE = False
try:
    from src.utils.secure_key_manager import SecureKeyManager, is_key_encrypted
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(_base_dir) == "src":
        _base_dir = os.path.dirname(_base_dir)
    _secure_key_manager = SecureKeyManager(_base_dir)
    _SECURE_KEY_AVAILABLE = True
except ImportError:
    pass

# Define required keys and their placeholder values to check against.
# If the value matches the placeholder OR is empty, prompt the user.
REQUIRED_KEYS = {
    "GEMINI_API_KEY": {
        "description": "Gemini API Key (Get it from https://aistudio.google.com/)",
        "placeholder": "YOUR_GEMINI_API_KEY_HERE",
        "encrypt": True,  # Flag to indicate this key should be encrypted
    }
}

# Optional keys - if missing, we'll add them with defaults from .env.example
# These won't prompt the user, but will be populated from the example file.
OPTIONAL_KEYS = [
    "INITIAL_WAIT",
    "POST_ACTION_WAIT",
    "SWITCH_QUESTION_WAIT",
    "POLL_INTERVAL",
    "MAX_RETRIES",
    "MOUSE_MOVE_DURATION",
    "HANDLE_DESCRIPTIVE_ANSWERS",
    "ENABLE_DETAILED_MODE",
    "TYPING_WPM_MIN",
    "TYPING_WPM_MAX",
    "DEVELOPER_MODE",
    "VERBOSE_STARTUP",
    "DEV_MAX_ITERATIONS",
    "DEV_SAVE_SCREENSHOTS",
    "MANUAL_MODE",
    "HOTKEY_MCQ",
    "HOTKEY_DESCRIPTIVE",
    "HOTKEY_DELAY",
    "URGENT_MODE",
    "GITHUB_REPO_OWNER",
    "GITHUB_REPO_NAME",
    "UPDATE_CHECK_INTERVAL_SECONDS",
]


def parse_env_file(filepath):
    """Parse a .env file and return a dict of key-value pairs."""
    values = {}
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    parts = line.split("=", 1)
                    key = parts[0].strip()
                    val = parts[1].strip()
                    values[key] = val
    return values


def validate_env():
    """
    Ensures .env exists and contains valid values for required variables.
    Prompts the user if values are missing or match the default placeholders.
    """
    print("[SETUP] Validating configuration...")

    # 1. Ensure .env exists
    if not os.path.exists(ENV_PATH):
        print(f"[SETUP] {ENV_PATH} not found. Creating from {EXAMPLE_PATH}...")
        if os.path.exists(EXAMPLE_PATH):
            shutil.copy(EXAMPLE_PATH, ENV_PATH)
        else:
            print(f"[ERROR] {EXAMPLE_PATH} missing. Creating minimal .env.")
            with open(ENV_PATH, "w", encoding="utf-8") as f:
                f.write("# Auto-generated .env\nGEMINI_API_KEY=\n")

    # 2. Read current .env content
    try:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[ERROR] Failed to read .env: {e}")
        return 1

    # 3. Parse current values
    current_values = parse_env_file(ENV_PATH)
    example_values = parse_env_file(EXAMPLE_PATH)

    new_lines = []
    keys_found = set()
    modified = False

    # 4. Process existing lines
    for line in lines:
        stripped = line.strip()
        # Preserve comments and empty lines
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        if "=" in stripped:
            parts = stripped.split("=", 1)
            key = parts[0].strip()
            val = parts[1].strip()
            keys_found.add(key)

            if key in REQUIRED_KEYS:
                info = REQUIRED_KEYS[key]
                # Check if value is missing or matches the placeholder
                is_missing = not val
                is_placeholder = val == info["placeholder"]
                
                # Check if the value is already encrypted (treat as valid)
                is_encrypted = False
                if _SECURE_KEY_AVAILABLE and val:
                    is_encrypted = is_key_encrypted(val)

                if (is_missing or is_placeholder) and not is_encrypted:
                    print(f"\n[CONFIG] Action Required: {key}")
                    print(f"         {info['description']}")

                    user_input = input(f"         Enter value for {key}: ").strip()

                    if user_input:
                        # Encrypt if required and available
                        value_to_save = user_input
                        if info.get("encrypt") and _SECURE_KEY_AVAILABLE and _secure_key_manager:
                            try:
                                value_to_save = _secure_key_manager.encrypt_key(user_input)
                                print(f"[SECURITY] {key} encrypted with machine-bound encryption.")
                            except Exception as e:
                                print(f"[WARNING] Could not encrypt {key}: {e}")
                        
                        line = f"{key}={value_to_save}\n"
                        modified = True
                        print(f"[INFO] Updated {key}.")
                    else:
                        print(f"[WARNING] Skipped {key}. Application may fail.")

        new_lines.append(line)

    # 5. Handle required keys that are completely missing from the file
    for key, info in REQUIRED_KEYS.items():
        if key not in keys_found:
            print(f"\n[CONFIG] Missing required variable: {key}")
            print(f"         {info['description']}")
            user_input = input(f"         Enter value for {key}: ").strip()

            if user_input:
                # Encrypt if required and available
                value_to_save = user_input
                if info.get("encrypt") and _SECURE_KEY_AVAILABLE and _secure_key_manager:
                    try:
                        value_to_save = _secure_key_manager.encrypt_key(user_input)
                        print(f"[SECURITY] {key} encrypted with machine-bound encryption.")
                    except Exception as e:
                        print(f"[WARNING] Could not encrypt {key}: {e}")
                
                new_lines.append(f"\n{key}={value_to_save}\n")
                modified = True
                print(f"[INFO] Added {key}.")
            else:
                print(f"[WARNING] Skipped {key}.")

    # 6. Add any missing optional keys with defaults from example
    for key in OPTIONAL_KEYS:
        if key not in keys_found and key in example_values:
            new_lines.append(f"{key}={example_values[key]}\n")
            modified = True

    # 7. Write back if modified
    if modified:
        try:
            with open(ENV_PATH, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            print("[SETUP] Configuration saved to .env.")
        except Exception as e:
            print(f"[ERROR] Failed to save .env: {e}")
            return 1
    else:
        print("[SETUP] Configuration OK.")

    return 0


if __name__ == "__main__":
    exit(validate_env())
