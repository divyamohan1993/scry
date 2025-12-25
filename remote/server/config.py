"""
Scry Remote - Server Configuration

Loads configuration from environment variables.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env file
ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(ENV_PATH)


def get_bool_env(key: str, default: bool = False) -> bool:
    """Helper to parse boolean env vars case-insensitively."""
    val = os.getenv(key, str(default)).lower()
    return val in ("true", "1", "yes", "on")


def get_int_env(key: str, default: int = 0) -> int:
    """Helper to parse integer env vars."""
    try:
        return int(os.getenv(key, default))
    except ValueError:
        return default


# =============================================================================
# GOOGLE OAUTH
# =============================================================================
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise ValueError(
        "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required. "
        "Set them in your .env file."
    )

# =============================================================================
# GEMINI API
# =============================================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is required. Set it in your .env file.")

# =============================================================================
# SERVER CONFIGURATION
# =============================================================================
DOMAIN = os.getenv("DOMAIN", "localhost")
PORT = get_int_env("PORT", 8000)
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
SESSION_TIMEOUT = get_int_env("SESSION_TIMEOUT", 3600)

# OAuth callback URL
OAUTH_REDIRECT_URI = f"https://{DOMAIN}/auth/callback"

# =============================================================================
# ACCESS CONTROL
# =============================================================================
_allowed_emails = os.getenv("ALLOWED_EMAILS", "")
ALLOWED_EMAILS = [e.strip() for e in _allowed_emails.split(",") if e.strip()]

# =============================================================================
# FRAME PROCESSING
# =============================================================================
FRAME_INTERVAL_MS = get_int_env("FRAME_INTERVAL_MS", 500)
FRAME_QUALITY = get_int_env("FRAME_QUALITY", 80)
MAX_SESSIONS = get_int_env("MAX_SESSIONS", 10)

# =============================================================================
# SCRY ADAPTER
# =============================================================================
SCRY_PATH = os.getenv("SCRY_PATH", str(Path(__file__).parent.parent.parent))
ENABLE_DETAILED_MODE = get_bool_env("ENABLE_DETAILED_MODE", True)

# =============================================================================
# LOGGING
# =============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DEBUG_MODE = get_bool_env("DEBUG_MODE", False)

# =============================================================================
# PATHS
# =============================================================================
BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / "client"
LOGS_DIR = BASE_DIR / "logs"
TEMP_DIR = BASE_DIR / "temp"

# Create directories
LOGS_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)
