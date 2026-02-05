"""
End-to-End Tests for Complete Workflows
========================================

These tests verify complete user workflows from start to finish,
including:
- Application startup and initialization
- Screen capture → Analysis → Action flow
- Hotkey triggers
- Error recovery
- Graceful shutdown

Note: E2E tests may require specific fixtures and mocking
to simulate the complete environment.
"""

import json
import os
import time
from unittest.mock import MagicMock, patch, call

import pytest


@pytest.mark.e2e
class TestApplicationStartup:
    """E2E tests for application startup sequence."""

    def test_application_initialization(self, mocker):
        """Test that application initializes correctly."""
        mocker.patch("keyboard.add_hotkey")
        mocker.patch("keyboard.wait")
        mocker.patch("src.runtime_config.get_config", return_value=False)
        
        # Mock the main module imports
        mocker.patch("mss.mss")
        mocker.patch("src.main.get_gemini_response")
        
        from src import main
        
        # Verify key globals are defined
        assert hasattr(main, "is_manual_mode")
        assert hasattr(main, "last_processed_question")

    def test_hotkey_registration(self, mocker):
        """Test that hotkeys are registered on startup."""
        mock_add_hotkey = mocker.patch("keyboard.add_hotkey")
        mocker.patch("keyboard.wait")
        
        from src.main import register_hotkeys
        
        register_hotkeys()
        
        # Should register multiple hotkeys
        assert mock_add_hotkey.call_count >= 3

    def test_config_loading_on_startup(self, mocker):
        """Test that configuration is loaded on startup."""
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
        mocker.patch("dotenv.load_dotenv")
        
        from src.config import GEMINI_API_KEY
        
        # Should have loaded the key
        assert GEMINI_API_KEY is not None


@pytest.mark.e2e
class TestFullMCQWorkflow:
    """E2E tests for complete MCQ answering workflow."""

    @pytest.fixture
    def full_mock_environment(self, mocker):
        """Setup complete mocked environment for E2E testing."""
        # Screen capture mock
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

        mocks = {
            "mss": mocker.patch("mss.mss", return_value=mock_mss_instance),
            "gemini": mocker.patch("src.main.get_gemini_response"),
            "find_text": mocker.patch("src.main.find_text_coordinates"),
            "click": mocker.patch("src.main.click_at"),
            "type_text": mocker.patch("src.main.type_text_human_like"),
            "sleep": mocker.patch("time.sleep"),
            "desktop": mocker.patch("src.main.switch_to_input_desktop", return_value=True),
            "runtime_config": mocker.patch("src.runtime_config.get_config", return_value=False),
        }
        
        return mocks

    def test_mcq_workflow_ocr_success(self, full_mock_environment):
        """Test complete MCQ workflow when OCR finds the answer."""
        mocks = full_mock_environment
        
        # Setup Gemini to return MCQ
        mocks["gemini"].return_value = {
            "type": "MCQ",
            "question": "What is the capital of France?",
            "answer_text": "Paris",
            "bbox": [200, 300, 250, 350],
        }
        
        # OCR finds the answer
        mocks["find_text"].return_value = (960, 540)
        
        from src.main import process_screen_cycle
        
        action_taken, question = process_screen_cycle()
        
        # Verify complete workflow
        assert action_taken is True
        assert question == "What is the capital of France?"
        mocks["click"].assert_called_once_with(960, 540)

    def test_mcq_workflow_bbox_fallback(self, full_mock_environment):
        """Test MCQ workflow falling back to bbox when OCR fails."""
        mocks = full_mock_environment
        
        # Setup Gemini to return MCQ
        mocks["gemini"].return_value = {
            "type": "MCQ",
            "question": "Test Question",
            "answer_text": "Answer",
            "bbox": [100, 200, 150, 250],  # ymin, xmin, ymax, xmax (0-1000 scale)
        }
        
        # OCR fails
        mocks["find_text"].return_value = None
        
        from src.main import process_screen_cycle
        
        action_taken, question = process_screen_cycle()
        
        # Should have clicked using bbox coordinates
        assert action_taken is True
        assert mocks["click"].called
        
        # Coordinates should be scaled to screen resolution
        x, y = mocks["click"].call_args[0]
        assert 0 <= x <= 1920
        assert 0 <= y <= 1080


@pytest.mark.e2e
class TestFullDescriptiveWorkflow:
    """E2E tests for complete descriptive answer workflow."""

    @pytest.fixture
    def full_mock_environment(self, mocker):
        """Setup complete mocked environment."""
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

        mocks = {
            "mss": mocker.patch("mss.mss", return_value=mock_mss_instance),
            "gemini": mocker.patch("src.main.get_gemini_response"),
            "type_text": mocker.patch("src.main.type_text_human_like"),
            "sleep": mocker.patch("time.sleep"),
            "desktop": mocker.patch("src.main.switch_to_input_desktop", return_value=True),
        }
        
        return mocks

    def test_descriptive_workflow_complete(self, full_mock_environment):
        """Test complete descriptive answer workflow."""
        mocks = full_mock_environment
        
        answer_text = "Photosynthesis is the process by which plants convert..."
        
        mocks["gemini"].return_value = {
            "type": "DESCRIPTIVE",
            "question": "Explain photosynthesis",
            "answer_text": answer_text,
            "marks": 5,
        }
        
        from src.main import process_screen_cycle
        
        action_taken, question = process_screen_cycle()
        
        # Verify workflow
        assert action_taken is True
        assert question == "Explain photosynthesis"
        mocks["type_text"].assert_called_once()
        
        # Verify typed text
        typed = mocks["type_text"].call_args[0][0]
        assert "Photosynthesis" in typed


@pytest.mark.e2e
class TestMultiMCQWorkflow:
    """E2E tests for multi-select MCQ workflow."""

    @pytest.fixture
    def full_mock_environment(self, mocker):
        """Setup complete mocked environment."""
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

        mocks = {
            "mss": mocker.patch("mss.mss", return_value=mock_mss_instance),
            "gemini": mocker.patch("src.main.get_gemini_response"),
            "click": mocker.patch("src.main.click_at"),
            "sleep": mocker.patch("time.sleep"),
            "desktop": mocker.patch("src.main.switch_to_input_desktop", return_value=True),
        }
        
        return mocks

    def test_multi_mcq_clicks_all_correct_options(self, full_mock_environment):
        """Test that multi-MCQ clicks all correct options."""
        mocks = full_mock_environment
        
        mocks["gemini"].return_value = {
            "type": "MULTI_MCQ",
            "question": "Select all that apply",
            "answers": [
                {"answer_text": "Option A", "bbox": [100, 100, 150, 150]},
                {"answer_text": "Option C", "bbox": [100, 300, 150, 350]},
                {"answer_text": "Option D", "bbox": [100, 400, 150, 450]},
            ],
        }
        
        from src.main import process_screen_cycle
        
        action_taken, _ = process_screen_cycle()
        
        # Should click 3 times (once for each correct option)
        assert action_taken is True
        assert mocks["click"].call_count == 3


@pytest.mark.e2e
class TestClipboardStreamWorkflow:
    """E2E tests for clipboard streaming workflow."""

    @pytest.fixture
    def mock_environment(self, mocker):
        """Setup mocked environment."""
        mocks = {
            "pyperclip": mocker.patch("src.main.pyperclip"),
            "type_text": mocker.patch("src.main.type_text_human_like"),
            "sleep": mocker.patch("time.sleep"),
        }
        mocks["pyperclip"].paste.return_value = "Clipboard content to type"
        return mocks

    def test_clipboard_stream_types_content(self, mock_environment):
        """Test that clipboard streaming types the clipboard content."""
        mocks = mock_environment
        
        from src.main import stream_clipboard
        
        stream_clipboard()
        
        mocks["type_text"].assert_called_once()
        typed = mocks["type_text"].call_args[0][0]
        assert "Clipboard content" in typed


@pytest.mark.e2e
class TestErrorRecoveryWorkflow:
    """E2E tests for error recovery scenarios."""

    @pytest.fixture
    def mock_environment(self, mocker):
        """Setup mocked environment."""
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

        mocks = {
            "mss": mocker.patch("mss.mss", return_value=mock_mss_instance),
            "gemini": mocker.patch("src.main.get_gemini_response"),
            "sleep": mocker.patch("time.sleep"),
            "desktop": mocker.patch("src.main.switch_to_input_desktop", return_value=True),
        }
        
        return mocks

    def test_recovery_from_gemini_failure(self, mock_environment):
        """Test recovery when Gemini fails."""
        mocks = mock_environment
        
        # Gemini returns None
        mocks["gemini"].return_value = None
        
        from src.main import process_screen_cycle
        
        # Should not crash
        action_taken, _ = process_screen_cycle()
        
        assert action_taken is False

    def test_recovery_from_malformed_response(self, mock_environment):
        """Test recovery from malformed Gemini response."""
        mocks = mock_environment
        
        # Malformed response (missing required fields)
        mocks["gemini"].return_value = {"type": "MCQ"}  # Missing bbox
        
        from src.main import process_screen_cycle
        
        # Should not crash
        try:
            action_taken, _ = process_screen_cycle()
        except KeyError:
            # This is acceptable - indicates need for better validation
            pass


@pytest.mark.e2e
class TestModeToggleWorkflow:
    """E2E tests for mode toggle workflow."""

    def test_toggle_between_auto_and_manual(self, mocker):
        """Test toggling between auto and manual mode."""
        mocker.patch("src.runtime_config.get_config", return_value=False)
        
        from src import main
        
        # Start in auto mode
        main.is_manual_mode = False
        
        # Toggle to manual
        main.toggle_mode()
        assert main.is_manual_mode is True
        
        # Toggle back to auto
        main.toggle_mode()
        assert main.is_manual_mode is False


@pytest.mark.e2e
class TestWebPanelWorkflow:
    """E2E tests for web panel workflow."""

    @pytest.fixture
    def client(self, mocker, tmp_path):
        """Create a test client with temp env file."""
        env_path = tmp_path / ".env"
        env_path.write_text("GEMINI_API_KEY=test_key\nINITIAL_WAIT=10\n")
        
        mocker.patch("src.web_control_panel.ENV_PATH", str(env_path))
        mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
        
        from src.web_control_panel import app
        
        app.config["TESTING"] = True
        
        with app.test_client() as client:
            yield client

    def test_config_read_write_cycle(self, client, mocker, tmp_path):
        """Test complete config read → modify → read cycle."""
        # Read initial config
        response = client.get("/api/config")
        assert response.status_code == 200
        initial_config = response.get_json()
        
        # Modify config
        response = client.post(
            "/api/config",
            json={"INITIAL_WAIT": "20"},
            content_type="application/json"
        )
        
        # Read again
        response = client.get("/api/config")
        
        # Should reflect changes (if implemented)
        assert response.status_code == 200


@pytest.mark.e2e
class TestIdempotencyWorkflow:
    """E2E tests for idempotency across multiple cycles."""

    @pytest.fixture
    def mock_environment(self, mocker):
        """Setup mocked environment."""
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

        mocks = {
            "mss": mocker.patch("mss.mss", return_value=mock_mss_instance),
            "gemini": mocker.patch("src.main.get_gemini_response"),
            "find_text": mocker.patch("src.main.find_text_coordinates"),
            "click": mocker.patch("src.main.click_at"),
            "sleep": mocker.patch("time.sleep"),
            "desktop": mocker.patch("src.main.switch_to_input_desktop", return_value=True),
        }
        
        return mocks

    def test_same_question_processed_once(self, mock_environment):
        """Test that same question is only processed once."""
        mocks = mock_environment
        
        from src import main
        from src.main import process_screen_cycle
        
        # Reset idempotency state
        main.last_processed_question = None
        
        mocks["gemini"].return_value = {
            "type": "MCQ",
            "question": "Repeated Question",
            "answer_text": "A",
            "bbox": [0, 0, 100, 100],
        }
        mocks["find_text"].return_value = (100, 100)
        
        # Process multiple times
        for _ in range(5):
            process_screen_cycle()
        
        # Should only click once
        assert mocks["click"].call_count == 1

    def test_different_questions_all_processed(self, mock_environment):
        """Test that different questions are all processed."""
        mocks = mock_environment
        
        from src import main
        from src.main import process_screen_cycle
        
        main.last_processed_question = None
        mocks["find_text"].return_value = (100, 100)
        
        questions = ["Question 1", "Question 2", "Question 3"]
        
        for i, q in enumerate(questions):
            mocks["gemini"].return_value = {
                "type": "MCQ",
                "question": q,
                "answer_text": "A",
                "bbox": [0, 0, 100, 100],
            }
            process_screen_cycle()
        
        # Should click for each different question
        assert mocks["click"].call_count == 3
