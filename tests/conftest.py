import os
import sys
from unittest.mock import MagicMock

import pytest

# Ensure src is in pythonpath
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Pre-emptive mocking for modules that might fail to import or have side effects
if "keyboard" not in sys.modules:
    sys.modules["keyboard"] = MagicMock()

if "pyautogui" not in sys.modules:
    sys.modules["pyautogui"] = MagicMock()

# Now we can safely define fixtures


@pytest.fixture
def mock_gemini_client(mocker):
    """Mocks the google.genai.Client"""
    mock_client = mocker.patch("src.gemini.client")
    return mock_client


@pytest.fixture
def mock_logger(mocker):
    """Mocks the logger"""
    return mocker.patch("src.logger.get_logger")


@pytest.fixture
def mock_mss(mocker):
    """Mocks mss used in main.py"""
    return mocker.patch("mss.mss")


@pytest.fixture
def mock_pyautogui(mocker):
    """Mocks pyautogui"""
    return mocker.patch("pyautogui.click")  # Mock specific functions as needed


@pytest.fixture
def mock_keyboard(mocker):
    """Mocks keyboard module"""
    return mocker.patch("src.main.keyboard")


@pytest.fixture
def mock_env_vars(mocker):
    """Mocks environment variables for config tests."""
    # NOTE: Since config.py loads env vars at IMPORT time, we need to
    # mock os.getenv BEFORE config is imported, OR reload it.
    # A cleaner way for unit tests is to mock os.getenv and then reload the module.
    return mocker.patch("os.getenv")
