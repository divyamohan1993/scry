"""
Scry Test Configuration and Fixtures
=====================================

This module provides comprehensive test fixtures and configuration for the entire
test suite. It follows enterprise testing patterns with:

- Dependency injection via fixtures
- Mock isolation for external services
- Parametrized test data factories
- Test environment setup and teardown
- Cross-cutting concerns (logging, metrics)

Usage:
    Fixtures are automatically discovered by pytest.
    Import fixtures by name in test functions.
"""

import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

# Ensure src is in pythonpath
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

# ============================================================================
# PRE-EMPTIVE MODULE MOCKING
# ============================================================================
# These modules have side effects on import or require Windows-specific APIs
# Mock them before any test code imports them

if "keyboard" not in sys.modules:
    mock_keyboard = MagicMock()
    mock_keyboard.KEY_DOWN = 0
    mock_keyboard.KEY_UP = 1
    sys.modules["keyboard"] = mock_keyboard

if "pyautogui" not in sys.modules:
    mock_pyautogui = MagicMock()
    mock_pyautogui.size.return_value = (1920, 1080)
    mock_pyautogui.position.return_value = (960, 540)
    sys.modules["pyautogui"] = mock_pyautogui

if "mss" not in sys.modules:
    mock_mss = MagicMock()
    sys.modules["mss"] = mock_mss


# ============================================================================
# DATA CLASSES FOR TEST FIXTURES
# ============================================================================


@dataclass
class MockGeminiResponse:
    """Factory for creating mock Gemini API responses."""

    type: str = "MCQ"
    question: str = "What is 2+2?"
    answer_text: str = "4"
    bbox: List[int] = field(default_factory=lambda: [100, 200, 150, 250])
    marks: Optional[int] = None
    
    def to_json(self) -> str:
        data = {
            "type": self.type,
            "question": self.question,
            "answer_text": self.answer_text,
            "bbox": self.bbox,
        }
        if self.marks is not None:
            data["marks"] = self.marks
        return json.dumps(data)
    
    def to_markdown_json(self) -> str:
        return f"```json\n{self.to_json()}\n```"


@dataclass
class MockScreenData:
    """Factory for creating mock screen capture data."""

    width: int = 1920
    height: int = 1080
    
    @property
    def bgra(self) -> bytes:
        return b"\x00" * (self.width * self.height * 4)
    
    @property
    def size(self) -> tuple:
        return (self.width, self.height)


@dataclass
class TestEnvironmentConfig:
    """Test environment configuration."""

    gemini_api_key: str = "TEST_API_KEY_123"
    manual_mode: bool = False
    developer_mode: bool = True
    initial_wait: int = 10
    poll_interval: int = 3
    mouse_move_duration: float = 0.8
    typing_wpm_min: int = 30
    typing_wpm_max: int = 70


# ============================================================================
# CORE FIXTURES
# ============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory that is automatically cleaned up."""
    temp = tempfile.mkdtemp(prefix="scry_test_")
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def temp_env_file(temp_dir):
    """Create a temporary .env file for testing."""
    env_path = os.path.join(temp_dir, ".env")
    example_path = os.path.join(temp_dir, ".env.example")
    
    env_content = """
GEMINI_API_KEY=TEST_KEY_123
INITIAL_WAIT=10
POLL_INTERVAL=3
MANUAL_MODE=False
DEVELOPER_MODE=True
"""
    
    with open(env_path, "w") as f:
        f.write(env_content)
    
    with open(example_path, "w") as f:
        f.write(env_content)
    
    return env_path


@pytest.fixture
def test_env_config():
    """Get test environment configuration."""
    return TestEnvironmentConfig()


# ============================================================================
# GEMINI CLIENT FIXTURES
# ============================================================================


@pytest.fixture
def mock_gemini_client(mocker):
    """Mock the google.genai.Client completely."""
    mock_client = mocker.patch("src.gemini.client")
    return mock_client


@pytest.fixture
def mock_gemini_response_factory():
    """Factory for creating Gemini response mocks."""
    def _factory(**kwargs):
        return MockGeminiResponse(**kwargs)
    return _factory


@pytest.fixture
def mock_gemini_mcq_response(mock_gemini_client):
    """Setup mock for a successful MCQ response."""
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "type": "MCQ",
        "question": "Test Question",
        "answer_text": "Option A",
        "bbox": [100, 100, 200, 200],
    })
    mock_gemini_client.models.generate_content.return_value = mock_response
    return mock_gemini_client


@pytest.fixture
def mock_gemini_descriptive_response(mock_gemini_client):
    """Setup mock for a successful descriptive response."""
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "type": "DESCRIPTIVE",
        "question": "Explain the concept",
        "answer_text": "This is a detailed explanation of the concept.",
        "marks": 5,
    })
    mock_gemini_client.models.generate_content.return_value = mock_response
    return mock_gemini_client


@pytest.fixture
def mock_gemini_safe_response(mock_gemini_client):
    """Setup mock for a SAFE (no action) response."""
    mock_response = MagicMock()
    mock_response.text = json.dumps({"type": "SAFE"})
    mock_gemini_client.models.generate_content.return_value = mock_response
    return mock_gemini_client


@pytest.fixture
def mock_gemini_multi_mcq_response(mock_gemini_client):
    """Setup mock for a multi-select MCQ response."""
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "type": "MULTI_MCQ",
        "question": "Select all correct answers",
        "answers": [
            {"answer_text": "Option A", "bbox": [100, 100, 150, 150]},
            {"answer_text": "Option C", "bbox": [200, 100, 250, 150]},
        ],
    })
    mock_gemini_client.models.generate_content.return_value = mock_response
    return mock_gemini_client


@pytest.fixture
def mock_gemini_error_then_success(mock_gemini_client):
    """Setup mock that fails first call then succeeds."""
    error_response = Exception("API temporarily unavailable")
    success_response = MagicMock()
    success_response.text = json.dumps({"type": "SAFE"})
    
    mock_gemini_client.models.generate_content.side_effect = [
        error_response,
        success_response,
    ]
    return mock_gemini_client


# ============================================================================
# SCREEN CAPTURE FIXTURES
# ============================================================================


@pytest.fixture
def mock_screen_data():
    """Get mock screen data."""
    return MockScreenData()


@pytest.fixture
def mock_mss(mocker, mock_screen_data):
    """Mock the mss screen capture library."""
    mock_mss_instance = MagicMock()
    mock_enter = MagicMock()
    mock_mss_instance.__enter__.return_value = mock_enter
    mock_mss_instance.__exit__ = MagicMock(return_value=False)
    
    # Mock screen grab
    mock_sct_img = MagicMock()
    mock_sct_img.size = mock_screen_data.size
    mock_sct_img.bgra = mock_screen_data.bgra
    mock_enter.grab.return_value = mock_sct_img
    mock_enter.monitors = [
        {},  # All monitors combined
        {"left": 0, "top": 0, "width": mock_screen_data.width, "height": mock_screen_data.height}
    ]
    
    return mocker.patch("mss.mss", return_value=mock_mss_instance)


@pytest.fixture
def mock_screen_capture(mock_mss):
    """Complete screen capture mock."""
    return mock_mss


# ============================================================================
# MOUSE AND KEYBOARD FIXTURES
# ============================================================================


@pytest.fixture
def mock_pyautogui(mocker):
    """Mock pyautogui module."""
    mock = MagicMock()
    mock.size.return_value = (1920, 1080)
    mock.position.return_value = (960, 540)
    mocker.patch.dict(sys.modules, {"pyautogui": mock})
    return mock


@pytest.fixture
def mock_click(mocker):
    """Mock click_at function."""
    return mocker.patch("src.main.click_at")


@pytest.fixture
def mock_mouse_move(mocker):
    """Mock human_like_move function."""
    return mocker.patch("src.utils.mouse.human_like_move")


@pytest.fixture
def mock_keyboard(mocker):
    """Mock keyboard module."""
    return mocker.patch("src.main.keyboard")


# ============================================================================
# TYPING ENGINE FIXTURES
# ============================================================================


@pytest.fixture
def mock_type_text(mocker):
    """Mock the type_text_human_like function."""
    return mocker.patch("src.main.type_text_human_like")


@pytest.fixture
def mock_typing_engine(mocker):
    """Mock the entire typing engine."""
    mock = MagicMock()
    mocker.patch("src.utils.typing_engine.HumanTypist", return_value=mock)
    return mock


# ============================================================================
# DESKTOP AND WINDOW FIXTURES
# ============================================================================


@pytest.fixture
def mock_desktop_manager(mocker):
    """Mock desktop manager functions."""
    mock_switch = mocker.patch(
        "src.main.switch_to_input_desktop", 
        return_value=True
    )
    return mock_switch


@pytest.fixture
def mock_find_text(mocker):
    """Mock find_text_coordinates function."""
    return mocker.patch("src.main.find_text_coordinates")


# ============================================================================
# LOGGING FIXTURES
# ============================================================================


@pytest.fixture
def mock_logger(mocker):
    """Mock the application logger."""
    return mocker.patch("src.logger.get_logger")


@pytest.fixture
def capture_logs(mocker):
    """Capture log output for assertions."""
    import logging
    
    log_messages = []
    
    class LogCapture(logging.Handler):
        def emit(self, record):
            log_messages.append({
                "level": record.levelname,
                "message": record.getMessage(),
                "name": record.name,
            })
    
    handler = LogCapture()
    handler.setLevel(logging.DEBUG)
    
    # Add to root logger
    logging.root.addHandler(handler)
    
    yield log_messages
    
    logging.root.removeHandler(handler)


# ============================================================================
# CONFIGURATION FIXTURES
# ============================================================================


@pytest.fixture
def mock_env_vars(mocker, test_env_config):
    """Mock environment variables with test configuration."""
    env_dict = {
        "GEMINI_API_KEY": test_env_config.gemini_api_key,
        "MANUAL_MODE": str(test_env_config.manual_mode),
        "DEVELOPER_MODE": str(test_env_config.developer_mode),
        "INITIAL_WAIT": str(test_env_config.initial_wait),
        "POLL_INTERVAL": str(test_env_config.poll_interval),
        "MOUSE_MOVE_DURATION": str(test_env_config.mouse_move_duration),
        "TYPING_WPM_MIN": str(test_env_config.typing_wpm_min),
        "TYPING_WPM_MAX": str(test_env_config.typing_wpm_max),
    }
    mocker.patch.dict(os.environ, env_dict, clear=True)
    return env_dict


@pytest.fixture
def mock_runtime_config(mocker):
    """Mock the runtime configuration."""
    mock_config = MagicMock()
    
    config_values = {
        "HOTKEY_DELAY": 2.0,
        "URGENT_MODE": False,
        "TYPING_WPM_MIN": 30,
        "TYPING_WPM_MAX": 70,
        "MANUAL_MODE": True,
    }
    
    mock_config.get.side_effect = lambda key, default=None: config_values.get(key, default)
    
    mocker.patch("src.runtime_config.runtime_config", mock_config)
    return mock_config


# ============================================================================
# SECURITY FIXTURES
# ============================================================================


@pytest.fixture
def mock_secure_key_manager(temp_dir):
    """Create a SecureKeyManager for testing."""
    from src.utils.secure_key_manager import SecureKeyManager
    return SecureKeyManager(temp_dir)


@pytest.fixture
def mock_license_manager(temp_dir):
    """Create a LicenseManager for testing."""
    from src.utils.license_manager import LicenseManager, CRYPTO_AVAILABLE
    if not CRYPTO_AVAILABLE:
        pytest.skip("cryptography package not available")
    return LicenseManager(temp_dir)


# ============================================================================
# IMAGE FIXTURES
# ============================================================================


@pytest.fixture
def mock_pil_image(mocker):
    """Create a mock PIL Image."""
    from PIL import Image
    import numpy as np
    
    # Create a simple test image
    img_array = np.zeros((100, 100, 3), dtype=np.uint8)
    img = Image.fromarray(img_array)
    return img


@pytest.fixture
def mock_screenshot(mock_pil_image):
    """Mock a screenshot capture."""
    return mock_pil_image


# ============================================================================
# TIME FIXTURES
# ============================================================================


@pytest.fixture
def mock_time(mocker):
    """Mock time functions for faster tests."""
    mock_sleep = mocker.patch("time.sleep")
    mock_time_func = mocker.patch("time.time", return_value=1000.0)
    return {"sleep": mock_sleep, "time": mock_time_func}


@pytest.fixture
def fast_time(mocker):
    """Make time pass instantly for tests."""
    mocker.patch("time.sleep", return_value=None)
    return True


# ============================================================================
# WEB CONTROL PANEL FIXTURES
# ============================================================================


@pytest.fixture
def mock_flask_app():
    """Create a test Flask app client."""
    # Delay import to avoid circular dependencies
    from src.web_control_panel import app
    
    app.config["TESTING"] = True
    app.config["DEBUG"] = False
    
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_subprocess(mocker):
    """Mock subprocess for process management tests."""
    mock_popen = mocker.patch("subprocess.Popen")
    mock_instance = MagicMock()
    mock_instance.poll.return_value = None  # Process running
    mock_instance.returncode = None
    mock_popen.return_value = mock_instance
    return mock_popen


# ============================================================================
# PARAMETRIZED TEST DATA
# ============================================================================


@pytest.fixture(params=[
    {"type": "MCQ", "answer_text": "Option A", "bbox": [100, 100, 200, 200]},
    {"type": "MCQ", "answer_text": "Option B", "bbox": [100, 200, 200, 300]},
    {"type": "DESCRIPTIVE", "answer_text": "Long answer", "marks": 5},
    {"type": "SAFE"},
])
def gemini_response_variants(request):
    """Parametrized Gemini response variants for comprehensive testing."""
    return request.param


@pytest.fixture(params=[
    "a", "z", "m", "c", "l",  # Valid hotkeys
])
def valid_hotkeys(request):
    """Parametrized valid hotkey values."""
    return request.param


@pytest.fixture(params=[
    (1920, 1080),
    (2560, 1440),
    (3840, 2160),
    (1366, 768),
])
def screen_resolutions(request):
    """Parametrized screen resolutions for testing."""
    return request.param


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_state():
    """Cleanup global state between tests."""
    yield
    # Reset any global state after each test
    # Import main module only if it's been imported
    if "src.main" in sys.modules:
        import src.main
        src.main.last_processed_question = None


@pytest.fixture(autouse=True)
def isolate_tests(mocker):
    """Ensure tests are isolated from external dependencies."""
    # Block network calls
    mocker.patch("socket.socket")
    yield


# ============================================================================
# MARKERS
# ============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "security: marks tests as security tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "windows: marks tests that require Windows"
    )
