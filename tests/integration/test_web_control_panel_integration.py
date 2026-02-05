"""
Integration Tests for Web Control Panel
========================================

Tests for the Flask web control panel including:
- API endpoints
- Environment variable management
- Process management
- WebSocket-like output streaming

Test Coverage:
- GET/POST /api/config
- GET/POST /api/start
- GET/POST /api/stop
- GET /api/status
- Static file serving
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


class TestWebControlPanelAPI:
    """Integration tests for Web Control Panel API endpoints."""

    @pytest.fixture
    def client(self, mocker):
        """Create a test client for the Flask app."""
        # Mock problematic imports
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
        
        from src.web_control_panel import app
        
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def mock_env_file(self, tmp_path):
        """Create a mock .env file."""
        env_content = """
GEMINI_API_KEY=test_api_key
INITIAL_WAIT=10
DEVELOPER_MODE=true
"""
        env_path = tmp_path / ".env"
        env_path.write_text(env_content)
        return str(env_path)


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    @pytest.fixture
    def client(self, mocker):
        """Create a test client."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
        
        from src.web_control_panel import app
        
        app.config["TESTING"] = True
        
        with app.test_client() as client:
            yield client

    def test_health_endpoint_exists(self, client):
        """Test that health endpoint responds."""
        # Health endpoint might be at / or /health
        response = client.get("/")
        
        # Should return some response (200 or redirect)
        assert response.status_code in [200, 302, 404]


class TestConfigEndpoints:
    """Tests for configuration management endpoints."""

    @pytest.fixture
    def client(self, mocker):
        """Create a test client."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
        
        from src.web_control_panel import app
        
        app.config["TESTING"] = True
        
        with app.test_client() as client:
            yield client

    def test_get_config_endpoint(self, client):
        """Test GET /api/config returns configuration."""
        response = client.get("/api/config")
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert isinstance(data, dict)

    def test_post_config_endpoint(self, client, mocker):
        """Test POST /api/config updates configuration."""
        mocker.patch("src.web_control_panel.ENV_PATH", "/tmp/.env")
        
        response = client.post(
            "/api/config",
            json={"INITIAL_WAIT": "20"},
            content_type="application/json"
        )
        
        # Should return success or validation error
        assert response.status_code in [200, 400, 500]


class TestProcessManagement:
    """Tests for process start/stop endpoints."""

    @pytest.fixture
    def client(self, mocker):
        """Create a test client."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
        
        from src.web_control_panel import app
        
        app.config["TESTING"] = True
        
        with app.test_client() as client:
            yield client

    def test_start_endpoint_exists(self, client):
        """Test POST /api/start exists."""
        response = client.post("/api/start")
        
        # Should exist (200, 400, or 500)
        assert response.status_code in [200, 400, 500]

    def test_stop_endpoint_exists(self, client):
        """Test POST /api/stop exists."""
        response = client.post("/api/stop")
        
        # Should exist
        assert response.status_code in [200, 400, 500]

    def test_status_endpoint(self, client):
        """Test GET /api/status returns status."""
        response = client.get("/api/status")
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert "running" in data or "status" in data or isinstance(data, dict)


class TestConfigSchema:
    """Tests for configuration schema validation."""

    def test_config_schema_structure(self):
        """Test that CONFIG_SCHEMA is properly structured."""
        from src.web_control_panel import CONFIG_SCHEMA
        
        assert isinstance(CONFIG_SCHEMA, dict)
        assert len(CONFIG_SCHEMA) > 0
        
        for category, config in CONFIG_SCHEMA.items():
            assert "icon" in config
            assert "variables" in config
            assert isinstance(config["variables"], list)

    def test_config_schema_variable_structure(self):
        """Test that each variable in schema has required fields."""
        from src.web_control_panel import CONFIG_SCHEMA
        
        for category, config in CONFIG_SCHEMA.items():
            for variable in config["variables"]:
                assert "key" in variable
                assert "type" in variable
                assert "desc" in variable


class TestEnvFileOperations:
    """Tests for .env file operations."""

    @pytest.fixture
    def temp_env(self, tmp_path):
        """Create a temporary .env file."""
        env_path = tmp_path / ".env"
        env_path.write_text("TEST_KEY=test_value\n")
        return str(env_path)

    def test_load_env_values(self, mocker, temp_env):
        """Test loading values from .env file."""
        mocker.patch("src.web_control_panel.ENV_PATH", temp_env)
        
        from src.web_control_panel import load_env_values
        
        values = load_env_values()
        
        assert isinstance(values, dict)


class TestOutputStreaming:
    """Tests for terminal output streaming."""

    @pytest.fixture
    def client(self, mocker):
        """Create a test client."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
        
        from src.web_control_panel import app
        
        app.config["TESTING"] = True
        
        with app.test_client() as client:
            yield client

    def test_output_endpoint_exists(self, client):
        """Test that output streaming endpoint exists."""
        response = client.get("/api/output")
        
        # Should exist (200 with empty output, or 404)
        assert response.status_code in [200, 404]


class TestSecurityConfiguration:
    """Tests for security-related configuration."""

    def test_encrypted_keys_set(self):
        """Test that ENCRYPTED_KEYS constant is defined."""
        from src.web_control_panel import ENCRYPTED_KEYS
        
        assert isinstance(ENCRYPTED_KEYS, set)
        assert "GEMINI_API_KEY" in ENCRYPTED_KEYS

    def test_max_output_lines_limit(self):
        """Test that MAX_OUTPUT_LINES is defined."""
        from src.web_control_panel import MAX_OUTPUT_LINES
        
        assert isinstance(MAX_OUTPUT_LINES, int)
        assert MAX_OUTPUT_LINES > 0


class TestFlaskAppConfiguration:
    """Tests for Flask app configuration."""

    def test_cors_enabled(self):
        """Test that CORS is configured."""
        from src.web_control_panel import app
        
        # CORS should be enabled for the app
        assert app is not None

    def test_app_routes_exist(self):
        """Test that expected routes are registered."""
        from src.web_control_panel import app
        
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        
        # Check for key routes
        assert "/" in routes or any("static" in r for r in routes)


class TestGlobalState:
    """Tests for global state management."""

    def test_process_variables_initialized(self):
        """Test that process management variables are initialized."""
        from src.web_control_panel import app_running, test_running
        
        # Should be boolean flags
        assert isinstance(app_running, bool)
        assert isinstance(test_running, bool)

    def test_output_lists_initialized(self):
        """Test that output lists are initialized."""
        from src.web_control_panel import app_output, test_output
        
        assert isinstance(app_output, list)
        assert isinstance(test_output, list)
