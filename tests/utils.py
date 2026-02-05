"""
Test Utilities and Helpers
===========================

This module provides reusable test utilities, factories, and helpers
for the entire test suite.
"""

import json
import os
import random
import string
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock


# =============================================================================
# DATA FACTORIES
# =============================================================================


@dataclass
class GeminiResponseFactory:
    """Factory for creating Gemini API response fixtures."""
    
    @staticmethod
    def mcq(
        question: str = "Sample MCQ question",
        answer: str = "Option A",
        bbox: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Create an MCQ response."""
        return {
            "type": "MCQ",
            "question": question,
            "answer_text": answer,
            "bbox": bbox or [100, 100, 200, 200],
        }
    
    @staticmethod
    def descriptive(
        question: str = "Sample descriptive question",
        answer: str = "Detailed answer text here.",
        marks: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a DESCRIPTIVE response."""
        response = {
            "type": "DESCRIPTIVE",
            "question": question,
            "answer_text": answer,
        }
        if marks is not None:
            response["marks"] = marks
        return response
    
    @staticmethod
    def multi_mcq(
        question: str = "Select all correct options",
        answers: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Create a MULTI_MCQ response."""
        if answers is None:
            answers = [
                {"answer_text": "A", "bbox": [100, 100, 150, 150]},
                {"answer_text": "C", "bbox": [200, 100, 250, 150]},
            ]
        return {
            "type": "MULTI_MCQ",
            "question": question,
            "answers": answers,
        }
    
    @staticmethod
    def safe() -> Dict[str, Any]:
        """Create a SAFE response."""
        return {"type": "SAFE"}
    
    @staticmethod
    def malformed() -> str:
        """Create a malformed response."""
        return "This is not valid JSON!!!"
    
    @staticmethod
    def with_markdown(data: Dict[str, Any]) -> str:
        """Wrap response in markdown code block."""
        return f"```json\n{json.dumps(data)}\n```"
    
    @staticmethod
    def random_mcq() -> Dict[str, Any]:
        """Create a random MCQ response."""
        options = ["A", "B", "C", "D"]
        bbox = [
            random.randint(50, 450),
            random.randint(50, 450),
            random.randint(500, 950),
            random.randint(500, 950),
        ]
        return {
            "type": "MCQ",
            "question": f"Random Question #{random.randint(1000, 9999)}",
            "answer_text": random.choice(options),
            "bbox": bbox,
        }


@dataclass
class ScreenCaptureFactory:
    """Factory for creating screen capture fixtures."""
    
    width: int = 1920
    height: int = 1080
    
    def create_mock_sct_img(self) -> MagicMock:
        """Create a mock screenshot image."""
        mock_img = MagicMock()
        mock_img.size = (self.width, self.height)
        mock_img.bgra = b"\x00" * (self.width * self.height * 4)
        return mock_img
    
    def create_mock_mss_context(self) -> MagicMock:
        """Create a mock mss context manager."""
        mock_mss = MagicMock()
        mock_enter = MagicMock()
        mock_mss.__enter__ = MagicMock(return_value=mock_enter)
        mock_mss.__exit__ = MagicMock(return_value=False)
        
        mock_enter.grab.return_value = self.create_mock_sct_img()
        mock_enter.monitors = [
            {},
            {"left": 0, "top": 0, "width": self.width, "height": self.height}
        ]
        
        return mock_mss


@dataclass
class EnvFileFactory:
    """Factory for creating .env file fixtures."""
    
    base_config: Dict[str, str] = field(default_factory=lambda: {
        "GEMINI_API_KEY": "TEST_API_KEY_123",
        "INITIAL_WAIT": "10",
        "POLL_INTERVAL": "3",
        "DEVELOPER_MODE": "true",
    })
    
    def create_env_file(self, temp_dir: str, overrides: Optional[Dict[str, str]] = None) -> str:
        """Create a .env file with the given configuration."""
        config = {**self.base_config}
        if overrides:
            config.update(overrides)
        
        env_path = os.path.join(temp_dir, ".env")
        
        with open(env_path, "w") as f:
            for key, value in config.items():
                f.write(f"{key}={value}\n")
        
        return env_path
    
    def create_env_example_file(self, temp_dir: str) -> str:
        """Create a .env.example file."""
        example_path = os.path.join(temp_dir, ".env.example")
        
        example_content = """
# Gemini API Key (required)
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE

# Timing settings
INITIAL_WAIT=10
POLL_INTERVAL=3

# Mode settings
DEVELOPER_MODE=false
MANUAL_MODE=false
"""
        
        with open(example_path, "w") as f:
            f.write(example_content)
        
        return example_path


# =============================================================================
# MOCK HELPERS
# =============================================================================


class MockHelpers:
    """Helper methods for setting up common mocks."""
    
    @staticmethod
    def create_gemini_mock(mocker, response_data: Dict[str, Any]) -> MagicMock:
        """Create a Gemini client mock with the given response."""
        mock_client = mocker.patch("src.gemini.client")
        mock_response = MagicMock()
        mock_response.text = json.dumps(response_data)
        mock_client.models.generate_content.return_value = mock_response
        return mock_client
    
    @staticmethod
    def create_screen_capture_mock(mocker, width: int = 1920, height: int = 1080) -> MagicMock:
        """Create a complete screen capture mock."""
        factory = ScreenCaptureFactory(width=width, height=height)
        return mocker.patch("mss.mss", return_value=factory.create_mock_mss_context())
    
    @staticmethod
    def create_keyboard_mock(mocker) -> Dict[str, MagicMock]:
        """Create keyboard-related mocks."""
        return {
            "add_hotkey": mocker.patch("keyboard.add_hotkey"),
            "on_press_key": mocker.patch("keyboard.on_press_key"),
            "wait": mocker.patch("keyboard.wait"),
            "is_pressed": mocker.patch("keyboard.is_pressed", return_value=False),
        }
    
    @staticmethod
    def create_full_environment_mock(mocker) -> Dict[str, MagicMock]:
        """Create all mocks needed for full environment testing."""
        return {
            "mss": MockHelpers.create_screen_capture_mock(mocker),
            "gemini": mocker.patch("src.main.get_gemini_response"),
            "find_text": mocker.patch("src.main.find_text_coordinates"),
            "click": mocker.patch("src.main.click_at"),
            "type_text": mocker.patch("src.main.type_text_human_like"),
            "sleep": mocker.patch("time.sleep"),
            "desktop": mocker.patch("src.main.switch_to_input_desktop", return_value=True),
            **MockHelpers.create_keyboard_mock(mocker),
        }


# =============================================================================
# ASSERTION HELPERS
# =============================================================================


class AssertionHelpers:
    """Custom assertion helpers for common test patterns."""
    
    @staticmethod
    def assert_response_valid_mcq(response: Dict[str, Any]) -> None:
        """Assert that a response is a valid MCQ response."""
        assert response is not None
        assert "type" in response
        assert response["type"] == "MCQ"
        assert "answer_text" in response
        assert "bbox" in response
        assert isinstance(response["bbox"], list)
        assert len(response["bbox"]) == 4
    
    @staticmethod
    def assert_response_valid_descriptive(response: Dict[str, Any]) -> None:
        """Assert that a response is a valid DESCRIPTIVE response."""
        assert response is not None
        assert "type" in response
        assert response["type"] == "DESCRIPTIVE"
        assert "answer_text" in response
    
    @staticmethod
    def assert_bbox_in_range(bbox: List[int], max_val: int = 1000) -> None:
        """Assert that bbox values are in valid range."""
        for val in bbox:
            assert 0 <= val <= max_val
    
    @staticmethod
    def assert_coordinates_on_screen(
        x: int, y: int, width: int = 1920, height: int = 1080
    ) -> None:
        """Assert that coordinates are within screen bounds."""
        assert 0 <= x <= width, f"X coordinate {x} out of bounds"
        assert 0 <= y <= height, f"Y coordinate {y} out of bounds"
    
    @staticmethod
    def assert_click_at_reasonable_position(mock_click: MagicMock) -> None:
        """Assert that click was at a reasonable position."""
        assert mock_click.called
        x, y = mock_click.call_args[0]
        AssertionHelpers.assert_coordinates_on_screen(x, y)
    
    @staticmethod
    def assert_text_contains_all(text: str, substrings: List[str]) -> None:
        """Assert that text contains all substrings."""
        for substring in substrings:
            assert substring in text, f"Missing substring: {substring}"


# =============================================================================
# RANDOM DATA GENERATORS
# =============================================================================


class RandomDataGenerators:
    """Generators for random test data."""
    
    @staticmethod
    def random_string(length: int = 10) -> str:
        """Generate a random alphanumeric string."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def random_api_key() -> str:
        """Generate a random API key-like string."""
        return f"AIzaSy{RandomDataGenerators.random_string(35)}"
    
    @staticmethod
    def random_question() -> str:
        """Generate a random question string."""
        prefixes = ["What is", "How does", "Explain", "Describe", "Why is"]
        topics = ["the theory", "this concept", "the process", "the mechanism"]
        return f"{random.choice(prefixes)} {random.choice(topics)}?"
    
    @staticmethod
    def random_bbox(scale: int = 1000) -> List[int]:
        """Generate random bbox values."""
        ymin = random.randint(0, scale // 2 - 1)
        xmin = random.randint(0, scale // 2 - 1)
        ymax = random.randint(scale // 2, scale)
        xmax = random.randint(scale // 2, scale)
        return [ymin, xmin, ymax, xmax]
    
    @staticmethod
    def random_coordinates(width: int = 1920, height: int = 1080) -> Tuple[int, int]:
        """Generate random screen coordinates."""
        return (random.randint(0, width), random.randint(0, height))


# =============================================================================
# TEMP FILE HELPERS
# =============================================================================


class TempFileHelpers:
    """Helpers for managing temporary files in tests."""
    
    @staticmethod
    def create_temp_dir() -> str:
        """Create a temporary directory."""
        return tempfile.mkdtemp(prefix="scry_test_")
    
    @staticmethod
    def create_temp_file(content: str, suffix: str = "") -> str:
        """Create a temporary file with content."""
        fd, path = tempfile.mkstemp(suffix=suffix, prefix="scry_test_")
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        return path
    
    @staticmethod
    def cleanup_temp_dir(path: str) -> None:
        """Safely remove a temporary directory."""
        import shutil
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass


# =============================================================================
# WAIT HELPERS
# =============================================================================


class WaitHelpers:
    """Helpers for waiting and timing in tests."""
    
    @staticmethod
    def wait_for_condition(
        condition_fn,
        timeout: float = 5.0,
        interval: float = 0.1,
    ) -> bool:
        """Wait for a condition to become true."""
        import time
        start = time.time()
        while time.time() - start < timeout:
            if condition_fn():
                return True
            time.sleep(interval)
        return False
    
    @staticmethod
    def measure_execution_time(func, *args, **kwargs) -> Tuple[Any, float]:
        """Measure execution time of a function."""
        import time
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        return result, elapsed
