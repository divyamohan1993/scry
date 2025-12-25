import os
from importlib import reload
from unittest.mock import patch

import pytest


class TestConfig:

    def reload_config(self):
        """Helper to reload config module to pick up new env vars."""
        # Patch load_dotenv GLOBALLY so imports inside the module get the mock
        with patch("dotenv.load_dotenv"):
            import src.config

            reload(src.config)
            return src.config

    def test_valid_api_key_load(self, mocker):
        """Test API key loading from env."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "TEST_KEY_123"}, clear=True)
        config = self.reload_config()
        assert config.GEMINI_API_KEY == "TEST_KEY_123"

    def test_missing_api_key_raises_error(self, mocker):
        """Test that missing API key raises ValueError."""
        mocker.patch.dict(os.environ, {}, clear=True)
        with pytest.raises(ValueError, match="GEMINI_API_KEY is not set"):
            self.reload_config()

    def test_boolean_env_parsing(self, mocker):
        """Test parsing of boolean strings."""
        env_vars = {
            "GEMINI_API_KEY": "dummy",
            "ENABLE_DETAILED_MODE": "true",  # Lowercase true
            "DEVELOPER_MODE": "FALSE",  # Uppercase FALSE
            "MANUAL_MODE": "1",  # 1 for True
        }
        mocker.patch.dict(os.environ, env_vars, clear=True)
        config = self.reload_config()

        assert config.ENABLE_DETAILED_MODE is True
        assert config.DEVELOPER_MODE is False
        assert config.MANUAL_MODE is True

    def test_int_float_parsing(self, mocker):
        """Test parsing of int and float values."""
        env_vars = {
            "GEMINI_API_KEY": "dummy",
            "INITIAL_WAIT": "50",
            "MOUSE_MOVE_DURATION": "1.5",
        }
        mocker.patch.dict(os.environ, env_vars, clear=True)
        config = self.reload_config()

        assert config.INITIAL_WAIT == 50
        assert config.MOUSE_MOVE_DURATION == 1.5

    def test_invalid_type_fallback(self, mocker):
        """Test fallback to defaults on invalid types."""
        env_vars = {"GEMINI_API_KEY": "dummy", "INITIAL_WAIT": "not_an_int"}
        mocker.patch.dict(os.environ, env_vars, clear=True)
        config = self.reload_config()

        # Should fall back to default (10) as defined in config.py
        assert config.INITIAL_WAIT == 10
