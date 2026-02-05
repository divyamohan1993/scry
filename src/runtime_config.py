"""
Runtime Configuration Manager for Scry

This module provides a centralized runtime configuration that can be updated
on-the-fly without restarting the application. It watches for config changes
and applies them immediately.

The config values are loaded from the .env file and can be refreshed at any time.
"""

import os
import time
import threading
from pathlib import Path
from typing import Dict, Any, Callable, Optional

from dotenv import load_dotenv

# =============================================================================
# RUNTIME CONFIG SINGLETON
# =============================================================================

class RuntimeConfig:
    """
    Singleton class that manages runtime configuration.
    Supports on-the-fly updates without restart.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._config: Dict[str, Any] = {}
        self._callbacks: Dict[str, list] = {}  # key -> list of callback functions
        self._env_path: Optional[Path] = None
        self._last_load_time: float = 0
        self._file_mod_time: float = 0
        
        # Initialize from config module
        self._setup_base_dir()
        self._load_all()
    
    def _setup_base_dir(self):
        """Setup base directory and .env path."""
        import sys
        IS_FROZEN = getattr(sys, 'frozen', False)
        
        if IS_FROZEN:
            BASE_DIR = os.path.dirname(sys.executable)
        else:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self._env_path = Path(BASE_DIR) / ".env"
    
    def _get_bool(self, key: str, default: bool = False) -> bool:
        """Parse boolean from environment."""
        val = os.getenv(key, str(default)).lower()
        return val in ("true", "1", "yes", "on")
    
    def _get_float(self, key: str, default: float = 0.0) -> float:
        """Parse float from environment."""
        try:
            return float(os.getenv(key, default))
        except ValueError:
            return default
    
    def _get_int(self, key: str, default: int = 0) -> int:
        """Parse int from environment."""
        try:
            return int(os.getenv(key, default))
        except ValueError:
            return default
    
    def _load_all(self):
        """Load all configuration values from .env file."""
        # Reload .env file
        if self._env_path and self._env_path.exists():
            load_dotenv(str(self._env_path), override=True)
            self._file_mod_time = os.path.getmtime(self._env_path)
        
        old_config = self._config.copy()
        
        # =================================================================
        # TIMING SETTINGS
        # =================================================================
        self._config["INITIAL_WAIT"] = self._get_int("INITIAL_WAIT", 10)
        self._config["POST_ACTION_WAIT"] = self._get_int("POST_ACTION_WAIT", 10)
        self._config["SWITCH_QUESTION_WAIT"] = self._get_int("SWITCH_QUESTION_WAIT", 5)
        self._config["POLL_INTERVAL"] = self._get_int("POLL_INTERVAL", 3)
        
        # =================================================================
        # RETRY SETTINGS
        # =================================================================
        self._config["MAX_RETRIES"] = self._get_int("MAX_RETRIES", 2)
        
        # =================================================================
        # MOUSE & TYPING SETTINGS
        # =================================================================
        self._config["MOUSE_MOVE_DURATION"] = self._get_float("MOUSE_MOVE_DURATION", 0.8)
        self._config["TYPING_WPM_MIN"] = self._get_int("TYPING_WPM_MIN", 30)
        self._config["TYPING_WPM_MAX"] = self._get_int("TYPING_WPM_MAX", 100)
        
        # =================================================================
        # FEATURE FLAGS
        # =================================================================
        self._config["HANDLE_DESCRIPTIVE_ANSWERS"] = self._get_bool("HANDLE_DESCRIPTIVE_ANSWERS", True)
        self._config["ENABLE_DETAILED_MODE"] = self._get_bool("ENABLE_DETAILED_MODE", True)
        self._config["URGENT_MODE"] = self._get_bool("URGENT_MODE", False)
        
        # =================================================================
        # HOTKEY SETTINGS (CONFIGURABLE TRIGGER KEYS)
        # =================================================================
        self._config["HOTKEY_MCQ"] = os.getenv("HOTKEY_MCQ", "q").lower()
        self._config["HOTKEY_DESCRIPTIVE"] = os.getenv("HOTKEY_DESCRIPTIVE", "z").lower()
        self._config["HOTKEY_CLIPBOARD"] = os.getenv("HOTKEY_CLIPBOARD", "c").lower()
        self._config["HOTKEY_MULTI_MCQ"] = os.getenv("HOTKEY_MULTI_MCQ", "m").lower()
        self._config["HOTKEY_TOGGLE_MODE"] = os.getenv("HOTKEY_TOGGLE_MODE", "t").lower()
        self._config["HOTKEY_DELAY"] = self._get_float("HOTKEY_DELAY", 2.0)
        
        # =================================================================
        # MODE SETTINGS
        # =================================================================
        self._config["MANUAL_MODE"] = self._get_bool("MANUAL_MODE", False)
        
        # =================================================================
        # DEVELOPER OPTIONS
        # =================================================================
        import sys
        IS_FROZEN = getattr(sys, 'frozen', False)
        if IS_FROZEN:
            self._config["DEVELOPER_MODE"] = False
            self._config["VERBOSE_STARTUP"] = False
        else:
            self._config["DEVELOPER_MODE"] = self._get_bool("DEVELOPER_MODE", False)
            self._config["VERBOSE_STARTUP"] = self._get_bool("VERBOSE_STARTUP", False)
        
        self._config["DEV_MAX_ITERATIONS"] = self._get_int("DEV_MAX_ITERATIONS", 2)
        self._config["DEV_SAVE_SCREENSHOTS"] = self._get_bool("DEV_SAVE_SCREENSHOTS", True) if not IS_FROZEN else False
        
        # =================================================================
        # UPDATE SETTINGS
        # =================================================================
        self._config["GITHUB_REPO_OWNER"] = os.getenv("GITHUB_REPO_OWNER", "divyamohan1993")
        self._config["GITHUB_REPO_NAME"] = os.getenv("GITHUB_REPO_NAME", "scry")
        self._config["UPDATE_CHECK_INTERVAL_SECONDS"] = self._get_int("UPDATE_CHECK_INTERVAL_SECONDS", 300)
        
        self._last_load_time = time.time()
        
        # Fire callbacks for changed values
        for key, new_value in self._config.items():
            old_value = old_config.get(key)
            if old_value != new_value and key in self._callbacks:
                for callback in self._callbacks[key]:
                    try:
                        callback(key, old_value, new_value)
                    except Exception as e:
                        print(f"[RuntimeConfig] Callback error for {key}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._config.get(key, default)
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values."""
        return self._config.copy()
    
    def reload(self) -> bool:
        """
        Reload configuration from .env file.
        Returns True if any values changed.
        """
        old_config = self._config.copy()
        self._load_all()
        return old_config != self._config
    
    def check_and_reload_if_changed(self) -> bool:
        """
        Check if .env file has been modified and reload if needed.
        Returns True if reloaded.
        """
        if self._env_path and self._env_path.exists():
            current_mod_time = os.path.getmtime(self._env_path)
            if current_mod_time > self._file_mod_time:
                return self.reload()
        return False
    
    def register_callback(self, key: str, callback: Callable[[str, Any, Any], None]):
        """
        Register a callback to be called when a config value changes.
        Callback signature: callback(key, old_value, new_value)
        """
        if key not in self._callbacks:
            self._callbacks[key] = []
        self._callbacks[key].append(callback)
    
    def unregister_callback(self, key: str, callback: Callable):
        """Unregister a callback."""
        if key in self._callbacks and callback in self._callbacks[key]:
            self._callbacks[key].remove(callback)


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================
runtime_config = RuntimeConfig()


# =============================================================================
# CONVENIENCE ACCESSORS
# =============================================================================
def get_config(key: str, default: Any = None) -> Any:
    """Get a runtime configuration value."""
    return runtime_config.get(key, default)

def reload_config() -> bool:
    """Force reload of configuration from .env file."""
    return runtime_config.reload()

def check_config_changes() -> bool:
    """Check for .env file changes and reload if needed."""
    return runtime_config.check_and_reload_if_changed()

def register_config_callback(key: str, callback: Callable[[str, Any, Any], None]):
    """Register a callback for config changes."""
    runtime_config.register_callback(key, callback)
