"""
Unit Tests for Configuration Module
====================================

Tests for config.py including:
- Environment variable loading
- Type parsing (bool, int, float)
- Default value handling
- API key validation
- Path configuration

Test Coverage:
- get_bool_env
- get_int_env
- get_float_env
- API key handling
- Path resolution
"""

import os
from importlib import reload
from unittest.mock import patch, MagicMock

import pytest


class TestBooleanEnvParsing:
    """Tests for boolean environment variable parsing."""

    def reload_config(self):
        """Helper to reload config module."""
        with patch("dotenv.load_dotenv"):
            import src.config
            reload(src.config)
            return src.config

    @pytest.mark.parametrize("value,expected", [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("1", True),
        ("yes", True),
        ("Yes", True),
        ("YES", True),
        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("0", False),
        ("no", False),
        ("No", False),
        ("NO", False),
    ])
    def test_boolean_values(self, mocker, value, expected):
        """Test various boolean string representations."""
        mocker.patch.dict(os.environ, {
            "GEMINI_API_KEY": "dummy_key",
            "DEVELOPER_MODE": value,
        }, clear=True)
        
        config = self.reload_config()
        assert config.DEVELOPER_MODE is expected

    def test_boolean_default_false(self, mocker):
        """Test that undefined boolean defaults to False."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "dummy"}, clear=True)
        config = self.reload_config()
        # DEVELOPER_MODE should default to False when not set
        assert config.DEVELOPER_MODE is False

    def test_boolean_invalid_string(self, mocker):
        """Test that invalid boolean string defaults to False."""
        mocker.patch.dict(os.environ, {
            "GEMINI_API_KEY": "dummy",
            "DEVELOPER_MODE": "invalid_value",
        }, clear=True)
        config = self.reload_config()
        assert config.DEVELOPER_MODE is False


class TestIntEnvParsing:
    """Tests for integer environment variable parsing."""

    def reload_config(self):
        """Helper to reload config module."""
        with patch("dotenv.load_dotenv"):
            import src.config
            reload(src.config)
            return src.config

    @pytest.mark.parametrize("value,expected", [
        ("10", 10),
        ("0", 0),
        ("100", 100),
        ("999", 999),
    ])
    def test_valid_integers(self, mocker, value, expected):
        """Test valid integer parsing."""
        mocker.patch.dict(os.environ, {
            "GEMINI_API_KEY": "dummy",
            "INITIAL_WAIT": value,
        }, clear=True)
        config = self.reload_config()
        assert config.INITIAL_WAIT == expected

    def test_invalid_integer_uses_default(self, mocker):
        """Test that invalid integer falls back to default."""
        mocker.patch.dict(os.environ, {
            "GEMINI_API_KEY": "dummy",
            "INITIAL_WAIT": "not_a_number",
        }, clear=True)
        config = self.reload_config()
        # Should use default value (10)
        assert config.INITIAL_WAIT == 10

    def test_negative_integer(self, mocker):
        """Test negative integer parsing."""
        mocker.patch.dict(os.environ, {
            "GEMINI_API_KEY": "dummy",
            "DEV_MAX_ITERATIONS": "-1",
        }, clear=True)
        config = self.reload_config()
        assert config.DEV_MAX_ITERATIONS == -1


class TestFloatEnvParsing:
    """Tests for float environment variable parsing."""

    def reload_config(self):
        """Helper to reload config module."""
        with patch("dotenv.load_dotenv"):
            import src.config
            reload(src.config)
            return src.config

    @pytest.mark.parametrize("value,expected", [
        ("0.5", 0.5),
        ("1.0", 1.0),
        ("1.5", 1.5),
        ("2.5", 2.5),
    ])
    def test_valid_floats(self, mocker, value, expected):
        """Test valid float parsing."""
        mocker.patch.dict(os.environ, {
            "GEMINI_API_KEY": "dummy",
            "MOUSE_MOVE_DURATION": value,
        }, clear=True)
        config = self.reload_config()
        assert config.MOUSE_MOVE_DURATION == expected

    def test_invalid_float_uses_default(self, mocker):
        """Test that invalid float falls back to default."""
        mocker.patch.dict(os.environ, {
            "GEMINI_API_KEY": "dummy",
            "MOUSE_MOVE_DURATION": "invalid",
        }, clear=True)
        config = self.reload_config()
        assert config.MOUSE_MOVE_DURATION == 0.8  # Default value


class TestApiKeyValidation:
    """Tests for API key validation and handling."""

    def reload_config(self):
        """Helper to reload config module."""
        with patch("dotenv.load_dotenv"):
            import src.config
            reload(src.config)
            return src.config

    def test_valid_api_key(self, mocker):
        """Test that valid API key is loaded correctly."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSy_valid_key_123"}, clear=True)
        config = self.reload_config()
        assert config.GEMINI_API_KEY == "AIzaSy_valid_key_123"

    def test_missing_api_key_raises_error(self, mocker):
        """Test that missing API key raises ValueError."""
        mocker.patch.dict(os.environ, {}, clear=True)
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            self.reload_config()

    def test_placeholder_api_key_raises_error(self, mocker):
        """Test that placeholder API key raises ValueError."""
        mocker.patch.dict(os.environ, {
            "GEMINI_API_KEY": "YOUR_GEMINI_API_KEY_HERE"
        }, clear=True)
        with pytest.raises(ValueError):
            self.reload_config()


class TestHotkeyConfiguration:
    """Tests for hotkey configuration."""

    def reload_config(self):
        """Helper to reload config module."""
        with patch("dotenv.load_dotenv"):
            import src.config
            reload(src.config)
            return src.config

    @pytest.mark.parametrize("hotkey_env,hotkey_attr,expected", [
        ("HOTKEY_MCQ", "HOTKEY_MCQ", "x"),
        ("HOTKEY_DESCRIPTIVE", "HOTKEY_DESCRIPTIVE", "z"),
        ("HOTKEY_CLIPBOARD", "HOTKEY_CLIPBOARD", "c"),
    ])
    def test_hotkey_defaults(self, mocker, hotkey_env, hotkey_attr, expected):
        """Test hotkey default values."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "dummy"}, clear=True)
        config = self.reload_config()
        assert getattr(config, hotkey_attr) == expected

    def test_custom_hotkey_value(self, mocker):
        """Test custom hotkey configuration."""
        mocker.patch.dict(os.environ, {
            "GEMINI_API_KEY": "dummy",
            "HOTKEY_MCQ": "a",
        }, clear=True)
        config = self.reload_config()
        assert config.HOTKEY_MCQ == "a"


class TestPathConfiguration:
    """Tests for path configuration."""

    def reload_config(self):
        """Helper to reload config module."""
        with patch("dotenv.load_dotenv"):
            import src.config
            reload(src.config)
            return src.config

    def test_base_dir_exists(self, mocker):
        """Test that BASE_DIR is set."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "dummy"}, clear=True)
        config = self.reload_config()
        assert config.BASE_DIR is not None
        assert len(config.BASE_DIR) > 0

    def test_screenshots_dir_defined(self, mocker):
        """Test that SCREENSHOTS_DIR is defined."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "dummy"}, clear=True)
        config = self.reload_config()
        assert hasattr(config, "SCREENSHOTS_DIR")


class TestTimingConfiguration:
    """Tests for timing-related configuration."""

    def reload_config(self):
        """Helper to reload config module."""
        with patch("dotenv.load_dotenv"):
            import src.config
            reload(src.config)
            return src.config

    def test_initial_wait_default(self, mocker):
        """Test INITIAL_WAIT default value."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "dummy"}, clear=True)
        config = self.reload_config()
        assert config.INITIAL_WAIT == 10

    def test_poll_interval_default(self, mocker):
        """Test POLL_INTERVAL default value."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "dummy"}, clear=True)
        config = self.reload_config()
        assert config.POLL_INTERVAL == 3

    def test_post_action_wait_default(self, mocker):
        """Test POST_ACTION_WAIT default value."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "dummy"}, clear=True)
        config = self.reload_config()
        assert config.POST_ACTION_WAIT == 2

    def test_custom_timing_values(self, mocker):
        """Test custom timing configuration."""
        mocker.patch.dict(os.environ, {
            "GEMINI_API_KEY": "dummy",
            "INITIAL_WAIT": "20",
            "POLL_INTERVAL": "5",
            "POST_ACTION_WAIT": "3",
        }, clear=True)
        config = self.reload_config()
        assert config.INITIAL_WAIT == 20
        assert config.POLL_INTERVAL == 5
        assert config.POST_ACTION_WAIT == 3


class TestFeatureFlags:
    """Tests for feature flag configuration."""

    def reload_config(self):
        """Helper to reload config module."""
        with patch("dotenv.load_dotenv"):
            import src.config
            reload(src.config)
            return src.config

    def test_handle_descriptive_answers_default(self, mocker):
        """Test HANDLE_DESCRIPTIVE_ANSWERS default."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "dummy"}, clear=True)
        config = self.reload_config()
        assert config.HANDLE_DESCRIPTIVE_ANSWERS is True

    def test_manual_mode_default(self, mocker):
        """Test MANUAL_MODE default."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "dummy"}, clear=True)
        config = self.reload_config()
        assert config.MANUAL_MODE is False

    def test_urgent_mode_default(self, mocker):
        """Test URGENT_MODE default."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "dummy"}, clear=True)
        config = self.reload_config()
        assert config.URGENT_MODE is False

    def test_enable_detailed_mode_default(self, mocker):
        """Test ENABLE_DETAILED_MODE default."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "dummy"}, clear=True)
        config = self.reload_config()
        assert config.ENABLE_DETAILED_MODE is False


class TestTypingConfiguration:
    """Tests for typing engine configuration."""

    def reload_config(self):
        """Helper to reload config module."""
        with patch("dotenv.load_dotenv"):
            import src.config
            reload(src.config)
            return src.config

    def test_typing_wpm_min_default(self, mocker):
        """Test TYPING_WPM_MIN default."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "dummy"}, clear=True)
        config = self.reload_config()
        assert config.TYPING_WPM_MIN == 30

    def test_typing_wpm_max_default(self, mocker):
        """Test TYPING_WPM_MAX default."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "dummy"}, clear=True)
        config = self.reload_config()
        assert config.TYPING_WPM_MAX == 100

    def test_typing_wpm_custom_values(self, mocker):
        """Test custom typing WPM values."""
        mocker.patch.dict(os.environ, {
            "GEMINI_API_KEY": "dummy",
            "TYPING_WPM_MIN": "40",
            "TYPING_WPM_MAX": "120",
        }, clear=True)
        config = self.reload_config()
        assert config.TYPING_WPM_MIN == 40
        assert config.TYPING_WPM_MAX == 120
