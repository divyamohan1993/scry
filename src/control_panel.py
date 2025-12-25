import os
import sys
import re
from pathlib import Path

# Try to import dotenv, but don't fail if not found (though it should be there)
try:
    from dotenv import load_dotenv, set_key
except ImportError:
    print("Error: python-dotenv not found. Please run 'pip install python-dotenv'")
    sys.exit(1)

# Import config to get default values and see what's actually being used
# We need to add the project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Define the variables we want to control
# We can hardcode this list based on our analysis of src/config.py
CONFIG_VARS = [
    {"key": "GEMINI_API_KEY", "type": "str", "desc": "API Key for Gemini AI"},
    {"key": "INITIAL_WAIT", "type": "int", "desc": "Seconds to wait before starting"},
    {"key": "POST_ACTION_WAIT", "type": "int", "desc": "Seconds to wait after an action"},
    {"key": "SWITCH_QUESTION_WAIT", "type": "int", "desc": "Seconds to wait when switching questions"},
    {"key": "POLL_INTERVAL", "type": "int", "desc": "Seconds between screen checks in Auto Mode"},
    {"key": "MAX_RETRIES", "type": "int", "desc": "Max retries for API calls"},
    {"key": "MOUSE_MOVE_DURATION", "type": "float", "desc": "Duration of mouse movement animation"},
    {"key": "HANDLE_DESCRIPTIVE_ANSWERS", "type": "bool", "desc": "Whether to handle descriptive questions"},
    {"key": "ENABLE_DETAILED_MODE", "type": "bool", "desc": "Enable handling of detailed/long answers"},
    {"key": "TYPING_WPM_MIN", "type": "int", "desc": "Minimum typing speed (WPM)"},
    {"key": "TYPING_WPM_MAX", "type": "int", "desc": "Maximum typing speed (WPM)"},
    {"key": "DEVELOPER_MODE", "type": "bool", "desc": "Show console, extra logging, no stealth"},
    {"key": "VERBOSE_STARTUP", "type": "bool", "desc": "Detailed startup logs"},
    {"key": "DEV_MAX_ITERATIONS", "type": "int", "desc": "Max loops in dev mode"},
    {"key": "DEV_SAVE_SCREENSHOTS", "type": "bool", "desc": "Save screenshots to disk"},
    {"key": "MANUAL_MODE", "type": "bool", "desc": "Use Hotkeys only (True) or Auto Loop (False)"},
    {"key": "HOTKEY_MCQ", "type": "str", "desc": "Hotkey for MCQ trigger"},
    {"key": "HOTKEY_DESCRIPTIVE", "type": "str", "desc": "Hotkey for Descriptive trigger"},
    {"key": "HOTKEY_DELAY", "type": "float", "desc": "Delay after hotkey before capture"},
    {"key": "URGENT_MODE", "type": "bool", "desc": "Urgent/Fast mode override"},
    {"key": "GITHUB_REPO_OWNER", "type": "str", "desc": "GitHub Owner for updates"},
    {"key": "GITHUB_REPO_NAME", "type": "str", "desc": "GitHub Repo Name for updates"},
    {"key": "UPDATE_CHECK_INTERVAL_SECONDS", "type": "int", "desc": "Update check frequency"},
]

ENV_PATH = PROJECT_ROOT / ".env"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def load_current_values():
    """Load values from .env directly."""
    values = {}
    if ENV_PATH.exists():
        with open(ENV_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    values[k.strip()] = v.strip()
    return values

def save_value(key, value):
    """Save a single value to .env using dotenv.set_key or fallback."""
    # Ensure file exists
    if not ENV_PATH.exists():
        with open(ENV_PATH, "w") as f:
            f.write("# Configuration File\n")
    
    # Update using set_key which handles quoting and existing keys well
    set_key(str(ENV_PATH), key, str(value))

def get_user_input(prompt, var_type):
    while True:
        val = input(prompt).strip()
        if var_type == "bool":
            if val.lower() in ["true", "1", "yes", "on", "t"]:
                return "True"
            if val.lower() in ["false", "0", "no", "off", "f"]:
                return "False"
            print("Invalid boolean. Use True/False.")
        elif var_type == "int":
            try:
                int(val)
                return val
            except ValueError:
                print("Invalid integer.")
        elif var_type == "float":
            try:
                float(val)
                return val
            except ValueError:
                print("Invalid float.")
        else:
            return val

def main():
    while True:
        clear_screen()
        print("================================================================")
        print(" SCREEN READER CONTROL PANEL")
        print("================================================================")
        print(f" Configuration File: {ENV_PATH}")
        print("================================================================")
        
        current_values = load_current_values()
        
        # Print table
        print(f"{'ID':<3} | {'KEY':<30} | {'CURRENT VALUE':<20} | {'DESCRIPTION'}")
        print("-" * 100)
        
        for idx, var in enumerate(CONFIG_VARS):
            key = var["key"]
            # Get value from .env, or "(Not Set)"
            val = current_values.get(key, "(Not Set)")
            # Truncate long values
            if len(str(val)) > 20:
                val = str(val)[:17] + "..."
            
            print(f"{idx+1:<3} | {key:<30} | {val:<20} | {var['desc']}")
            
        print("-" * 100)
        print("Enter the ID of the variable to edit, or 'q' to quit.")
        
        choice = input("> ").strip().lower()
        if choice == 'q':
            break
            
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(CONFIG_VARS):
                selected = CONFIG_VARS[idx]
                key = selected["key"]
                print(f"\nEditing {key}")
                print(f"Description: {selected['desc']}")
                print(f"Current Value: {current_values.get(key, '(Not Set)')}")
                
                new_val = get_user_input(f"Enter new value ({selected['type']}): ", selected["type"])
                save_value(key, new_val)
                print("Value updated!")
                input("Press Enter to continue...")
            else:
                print("Invalid ID.")
                input("Press Enter to continue...")
        except ValueError:
            print("Invalid input.")
            input("Press Enter to continue...")

if __name__ == "__main__":
    main()
