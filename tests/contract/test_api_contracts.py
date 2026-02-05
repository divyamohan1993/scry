"""
Contract Tests for API Interfaces
===================================

These tests verify that modules adhere to their expected interfaces.
They ensure backward compatibility and proper contract fulfillment.

Test Categories:
- Gemini response schema validation
- Configuration schema validation
- Inter-module contracts
- Return type contracts
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from unittest.mock import MagicMock

import pytest


@pytest.mark.contract
class TestGeminiResponseContract:
    """Contract tests for Gemini response format."""

    @pytest.fixture
    def valid_mcq_response(self):
        """Valid MCQ response structure."""
        return {
            "type": "MCQ",
            "question": "Sample question text",
            "answer_text": "Sample answer",
            "bbox": [100, 200, 150, 250],  # ymin, xmin, ymax, xmax
        }

    @pytest.fixture
    def valid_descriptive_response(self):
        """Valid DESCRIPTIVE response structure."""
        return {
            "type": "DESCRIPTIVE",
            "question": "Explain concept",
            "answer_text": "Detailed explanation here",
            "marks": 5,
        }

    @pytest.fixture
    def valid_multi_mcq_response(self):
        """Valid MULTI_MCQ response structure."""
        return {
            "type": "MULTI_MCQ",
            "question": "Select all correct options",
            "answers": [
                {"answer_text": "Option A", "bbox": [100, 100, 150, 150]},
                {"answer_text": "Option B", "bbox": [200, 100, 250, 150]},
            ],
        }

    @pytest.fixture
    def valid_safe_response(self):
        """Valid SAFE response structure."""
        return {"type": "SAFE"}

    def test_mcq_response_has_required_fields(self, valid_mcq_response):
        """Test MCQ response has all required fields."""
        required_fields = ["type", "answer_text", "bbox"]
        
        for field in required_fields:
            assert field in valid_mcq_response, f"Missing required field: {field}"

    def test_mcq_response_type_is_mcq(self, valid_mcq_response):
        """Test MCQ response has correct type."""
        assert valid_mcq_response["type"] == "MCQ"

    def test_mcq_bbox_is_list_of_four(self, valid_mcq_response):
        """Test MCQ bbox is a list of 4 numbers."""
        bbox = valid_mcq_response["bbox"]
        
        assert isinstance(bbox, list)
        assert len(bbox) == 4
        assert all(isinstance(x, (int, float)) for x in bbox)

    def test_mcq_bbox_values_in_range(self, valid_mcq_response):
        """Test MCQ bbox values are in valid range (0-1000)."""
        bbox = valid_mcq_response["bbox"]
        
        for val in bbox:
            assert 0 <= val <= 1000

    def test_descriptive_response_has_required_fields(self, valid_descriptive_response):
        """Test DESCRIPTIVE response has all required fields."""
        required_fields = ["type", "answer_text"]
        
        for field in required_fields:
            assert field in valid_descriptive_response

    def test_descriptive_response_marks_optional(self, valid_descriptive_response):
        """Test DESCRIPTIVE response marks field is optional."""
        del valid_descriptive_response["marks"]
        
        # Should still be valid
        assert "type" in valid_descriptive_response
        assert "answer_text" in valid_descriptive_response

    def test_multi_mcq_answers_is_list(self, valid_multi_mcq_response):
        """Test MULTI_MCQ answers is a list."""
        answers = valid_multi_mcq_response["answers"]
        
        assert isinstance(answers, list)
        assert len(answers) > 0

    def test_multi_mcq_answer_has_required_fields(self, valid_multi_mcq_response):
        """Test each answer in MULTI_MCQ has required fields."""
        for answer in valid_multi_mcq_response["answers"]:
            assert "answer_text" in answer
            assert "bbox" in answer

    def test_safe_response_only_needs_type(self, valid_safe_response):
        """Test SAFE response only requires type field."""
        assert "type" in valid_safe_response
        assert valid_safe_response["type"] == "SAFE"
        assert len(valid_safe_response) == 1


@pytest.mark.contract
class TestConfigurationContract:
    """Contract tests for configuration module."""

    def test_required_config_exports(self):
        """Test that config module exports required values."""
        from src import config
        
        required_exports = [
            "GEMINI_API_KEY",
            "INITIAL_WAIT",
            "POLL_INTERVAL",
            "DEVELOPER_MODE",
            "MANUAL_MODE",
        ]
        
        for export in required_exports:
            assert hasattr(config, export), f"Missing export: {export}"

    def test_gemini_api_key_is_string(self):
        """Test GEMINI_API_KEY is a string."""
        from src.config import GEMINI_API_KEY
        
        assert isinstance(GEMINI_API_KEY, str)

    def test_initial_wait_is_integer(self, mocker):
        """Test INITIAL_WAIT is an integer."""
        mocker.patch.dict("os.environ", {"GEMINI_API_KEY": "test"})
        
        from src.config import INITIAL_WAIT
        
        assert isinstance(INITIAL_WAIT, int)
        assert INITIAL_WAIT >= 0

    def test_poll_interval_is_integer(self, mocker):
        """Test POLL_INTERVAL is an integer."""
        mocker.patch.dict("os.environ", {"GEMINI_API_KEY": "test"})
        
        from src.config import POLL_INTERVAL
        
        assert isinstance(POLL_INTERVAL, int)
        assert POLL_INTERVAL >= 0


@pytest.mark.contract
class TestRuntimeConfigContract:
    """Contract tests for runtime configuration."""

    def test_get_config_returns_value_or_default(self, mocker):
        """Test get_config returns a value."""
        mocker.patch("dotenv.load_dotenv")
        
        from src.runtime_config import get_config
        
        result = get_config("NONEXISTENT_KEY", "default_value")
        
        # Should return the default
        assert result == "default_value"

    def test_get_config_signature(self):
        """Test get_config has expected signature."""
        from src.runtime_config import get_config
        import inspect
        
        sig = inspect.signature(get_config)
        params = list(sig.parameters.keys())
        
        assert "key" in params
        assert "default" in params

    def test_register_callback_signature(self):
        """Test register_config_callback has expected signature."""
        from src.runtime_config import register_config_callback
        import inspect
        
        sig = inspect.signature(register_config_callback)
        params = list(sig.parameters.keys())
        
        assert "key" in params
        assert "callback" in params


@pytest.mark.contract
class TestSecureKeyManagerContract:
    """Contract tests for SecureKeyManager."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create a SecureKeyManager instance."""
        from src.utils.secure_key_manager import SecureKeyManager
        return SecureKeyManager(str(tmp_path))

    def test_encrypt_returns_string(self, manager):
        """Test encrypt_key returns a string."""
        result = manager.encrypt_key("test_key")
        
        assert isinstance(result, str)

    def test_encrypt_returns_prefixed_string(self, manager):
        """Test encrypt_key returns prefixed string."""
        result = manager.encrypt_key("test_key")
        
        assert result.startswith("SCRY_ENC_V1:")

    def test_decrypt_returns_string_or_none(self, manager):
        """Test decrypt_key returns string or None."""
        encrypted = manager.encrypt_key("test_key")
        result = manager.decrypt_key(encrypted)
        
        assert result is None or isinstance(result, str)

    def test_is_key_encrypted_returns_bool(self):
        """Test is_key_encrypted returns boolean."""
        from src.utils.secure_key_manager import is_key_encrypted
        
        result1 = is_key_encrypted("plain_text")
        result2 = is_key_encrypted("SCRY_ENC_V1:encrypted")
        
        assert isinstance(result1, bool)
        assert isinstance(result2, bool)


@pytest.mark.contract
class TestGeminiModuleContract:
    """Contract tests for Gemini module."""

    def test_get_gemini_response_signature(self, mocker):
        """Test get_gemini_response has expected signature."""
        mocker.patch("src.gemini.client")
        
        from src.gemini import get_gemini_response
        import inspect
        
        sig = inspect.signature(get_gemini_response)
        params = list(sig.parameters.keys())
        
        assert "image" in params or "pil_image" in params or len(params) >= 1

    def test_get_gemini_response_returns_dict_or_none(self, mocker):
        """Test get_gemini_response returns dict or None."""
        mock_client = mocker.patch("src.gemini.client")
        mock_response = MagicMock()
        mock_response.text = '{"type": "SAFE"}'
        mock_client.models.generate_content.return_value = mock_response
        
        from src.gemini import get_gemini_response
        
        result = get_gemini_response(MagicMock())
        
        assert result is None or isinstance(result, dict)


@pytest.mark.contract
class TestMouseModuleContract:
    """Contract tests for mouse utilities."""

    def test_click_at_signature(self, mocker):
        """Test click_at has expected signature."""
        mocker.patch("src.utils.mouse.pyautogui")
        
        from src.utils.mouse import click_at
        import inspect
        
        sig = inspect.signature(click_at)
        params = list(sig.parameters.keys())
        
        assert "x" in params
        assert "y" in params

    def test_human_like_move_signature(self, mocker):
        """Test human_like_move has expected signature."""
        mocker.patch("src.utils.mouse.pyautogui")
        
        from src.utils.mouse import human_like_move
        import inspect
        
        sig = inspect.signature(human_like_move)
        params = list(sig.parameters.keys())
        
        # Should accept at least x, y coordinates
        assert len(params) >= 2


@pytest.mark.contract
class TestTypingEngineContract:
    """Contract tests for typing engine."""

    def test_human_typist_has_type_text_method(self, mocker):
        """Test HumanTypist has type_text method."""
        mocker.patch("keyboard.on_press_key")
        mocker.patch("src.runtime_config.get_config", return_value=False)
        
        from src.utils.typing_engine import HumanTypist
        
        typist = HumanTypist()
        
        assert hasattr(typist, "type_text")
        assert callable(typist.type_text)

    def test_human_typist_type_text_signature(self, mocker):
        """Test type_text method signature."""
        mocker.patch("keyboard.on_press_key")
        mocker.patch("src.runtime_config.get_config", return_value=False)
        
        from src.utils.typing_engine import HumanTypist
        import inspect
        
        typist = HumanTypist()
        sig = inspect.signature(typist.type_text)
        params = list(sig.parameters.keys())
        
        assert "text" in params


@pytest.mark.contract
class TestMainModuleContract:
    """Contract tests for main module."""

    def test_process_screen_cycle_returns_tuple(self, mocker):
        """Test process_screen_cycle returns expected tuple."""
        mock_mss_instance = MagicMock()
        mock_enter = MagicMock()
        mock_mss_instance.__enter__.return_value = mock_enter
        mock_mss_instance.__exit__ = MagicMock(return_value=False)

        mock_sct_img = MagicMock()
        mock_sct_img.size = (1920, 1080)
        mock_sct_img.bgra = b"\x00" * (1920 * 1080 * 4)
        mock_enter.grab.return_value = mock_sct_img
        mock_enter.monitors = [
            {},
            {"left": 0, "top": 0, "width": 1920, "height": 1080}
        ]

        mocker.patch("mss.mss", return_value=mock_mss_instance)
        mocker.patch("src.main.get_gemini_response", return_value={"type": "SAFE"})
        mocker.patch("src.main.switch_to_input_desktop", return_value=True)
        mocker.patch("time.sleep")
        
        from src.main import process_screen_cycle
        
        result = process_screen_cycle()
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)  # action_taken
        assert result[1] is None or isinstance(result[1], str)  # question_text

    def test_toggle_mode_changes_state(self, mocker):
        """Test toggle_mode modifies is_manual_mode."""
        mocker.patch("src.runtime_config.get_config", return_value=False)
        
        from src import main
        
        initial = main.is_manual_mode
        main.toggle_mode()
        
        assert main.is_manual_mode != initial


@pytest.mark.contract
class TestWebControlPanelContract:
    """Contract tests for web control panel."""

    def test_config_schema_structure(self):
        """Test CONFIG_SCHEMA has expected structure."""
        from src.web_control_panel import CONFIG_SCHEMA
        
        # Should be a dict
        assert isinstance(CONFIG_SCHEMA, dict)
        
        # Each category should have icon and variables
        for category, config in CONFIG_SCHEMA.items():
            assert "icon" in config
            assert "variables" in config
            assert isinstance(config["variables"], list)

    def test_load_env_values_returns_dict(self, mocker):
        """Test load_env_values returns a dictionary."""
        mocker.patch("src.web_control_panel.ENV_PATH", "/nonexistent/.env")
        mocker.patch("builtins.open", mocker.mock_open(read_data="KEY=value"))
        
        from src.web_control_panel import load_env_values
        
        result = load_env_values()
        
        assert isinstance(result, dict)

    def test_api_endpoints_exist(self, mocker):
        """Test that API endpoints are registered."""
        mocker.patch.dict("os.environ", {"GEMINI_API_KEY": "test"})
        
        from src.web_control_panel import app
        
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        
        expected_endpoints = ["/api/config", "/api/status"]
        
        for endpoint in expected_endpoints:
            assert any(endpoint in route for route in routes)
