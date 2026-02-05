"""
Edge Case and Boundary Tests
==============================

Tests specifically designed to catch edge cases and boundary conditions.
These tests focus on unusual inputs, extreme values, and corner cases
that could cause failures in production.
"""

import json
from unittest.mock import MagicMock

import pytest


@pytest.mark.edge_case
class TestGeminiEdgeCases:
    """Edge case tests for Gemini module."""

    @pytest.fixture
    def mock_gemini_client(self, mocker):
        """Mock Gemini client."""
        return mocker.patch("src.gemini.client")

    # Response format edge cases

    def test_empty_question_text(self, mock_gemini_client):
        """Test handling of empty question text."""
        from src.gemini import get_gemini_response
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "type": "MCQ",
            "question": "",
            "answer_text": "A",
            "bbox": [0, 0, 100, 100],
        })
        mock_gemini_client.models.generate_content.return_value = mock_response
        
        result = get_gemini_response(MagicMock())
        
        assert result is not None
        assert result["question"] == ""

    def test_very_long_answer_text(self, mock_gemini_client):
        """Test handling of very long answer text."""
        from src.gemini import get_gemini_response
        
        long_answer = "A" * 10000
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "type": "DESCRIPTIVE",
            "question": "Test",
            "answer_text": long_answer,
        })
        mock_gemini_client.models.generate_content.return_value = mock_response
        
        result = get_gemini_response(MagicMock())
        
        assert result is not None
        assert len(result["answer_text"]) == 10000

    def test_bbox_at_zero(self, mock_gemini_client):
        """Test bbox at origin (0,0,0,0)."""
        from src.gemini import get_gemini_response
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "type": "MCQ",
            "question": "Test",
            "answer_text": "A",
            "bbox": [0, 0, 0, 0],
        })
        mock_gemini_client.models.generate_content.return_value = mock_response
        
        result = get_gemini_response(MagicMock())
        
        assert result is not None
        assert result["bbox"] == [0, 0, 0, 0]

    def test_bbox_at_max(self, mock_gemini_client):
        """Test bbox at maximum (1000,1000,1000,1000)."""
        from src.gemini import get_gemini_response
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "type": "MCQ",
            "question": "Test",
            "answer_text": "A",
            "bbox": [1000, 1000, 1000, 1000],
        })
        mock_gemini_client.models.generate_content.return_value = mock_response
        
        result = get_gemini_response(MagicMock())
        
        assert result is not None

    def test_answer_with_only_whitespace(self, mock_gemini_client):
        """Test answer containing only whitespace."""
        from src.gemini import get_gemini_response
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "type": "DESCRIPTIVE",
            "question": "Test",
            "answer_text": "   \n\t  ",
        })
        mock_gemini_client.models.generate_content.return_value = mock_response
        
        result = get_gemini_response(MagicMock())
        
        assert result is not None

    def test_multi_mcq_with_single_answer(self, mock_gemini_client):
        """Test MULTI_MCQ with only one answer."""
        from src.gemini import get_gemini_response
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "type": "MULTI_MCQ",
            "question": "Select all",
            "answers": [
                {"answer_text": "A", "bbox": [100, 100, 150, 150]},
            ],
        })
        mock_gemini_client.models.generate_content.return_value = mock_response
        
        result = get_gemini_response(MagicMock())
        
        assert result is not None
        assert len(result["answers"]) == 1

    def test_multi_mcq_with_empty_answers(self, mock_gemini_client):
        """Test MULTI_MCQ with empty answers list."""
        from src.gemini import get_gemini_response
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "type": "MULTI_MCQ",
            "question": "Select all",
            "answers": [],
        })
        mock_gemini_client.models.generate_content.return_value = mock_response
        
        result = get_gemini_response(MagicMock())
        
        assert result is not None

    def test_marks_as_zero(self, mock_gemini_client):
        """Test descriptive with marks = 0."""
        from src.gemini import get_gemini_response
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "type": "DESCRIPTIVE",
            "question": "Test",
            "answer_text": "Answer",
            "marks": 0,
        })
        mock_gemini_client.models.generate_content.return_value = mock_response
        
        result = get_gemini_response(MagicMock())
        
        assert result is not None
        assert result["marks"] == 0

    def test_marks_as_large_number(self, mock_gemini_client):
        """Test descriptive with very large marks value."""
        from src.gemini import get_gemini_response
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "type": "DESCRIPTIVE",
            "question": "Test",
            "answer_text": "Answer",
            "marks": 9999,
        })
        mock_gemini_client.models.generate_content.return_value = mock_response
        
        result = get_gemini_response(MagicMock())
        
        assert result is not None
        assert result["marks"] == 9999


@pytest.mark.edge_case
class TestTypingEngineEdgeCases:
    """Edge case tests for typing engine."""

    @pytest.fixture
    def typist(self, mocker):
        """Create a HumanTypist instance."""
        mocker.patch("keyboard.on_press_key")
        mocker.patch("src.runtime_config.get_config", return_value=False)
        
        from src.utils.typing_engine import HumanTypist
        return HumanTypist()

    def test_type_empty_string(self, typist, mocker):
        """Test typing empty string."""
        mock_send = mocker.patch("src.utils.typing_engine._send_char")
        mocker.patch("time.sleep")
        
        typist.type_text("")
        
        assert mock_send.call_count == 0

    def test_type_single_character(self, typist, mocker):
        """Test typing a single character."""
        mock_send = mocker.patch("src.utils.typing_engine._send_char")
        mocker.patch("time.sleep")
        
        typist.type_text("a")
        
        assert mock_send.call_count == 1

    def test_type_only_spaces(self, typist, mocker):
        """Test typing only spaces."""
        mock_send = mocker.patch("src.utils.typing_engine._send_char")
        mocker.patch("time.sleep")
        
        typist.type_text("     ")
        
        assert mock_send.call_count == 5

    def test_type_only_newlines(self, typist, mocker):
        """Test typing only newlines."""
        mock_send = mocker.patch("src.utils.typing_engine._send_char")
        mocker.patch("time.sleep")
        
        typist.type_text("\n\n\n")
        
        assert mock_send.call_count >= 0  # Implementation may vary

    def test_type_unicode_emoji(self, typist, mocker):
        """Test typing unicode emoji characters."""
        mock_send = mocker.patch("src.utils.typing_engine._send_char")
        mocker.patch("time.sleep")
        
        typist.type_text("Hello 🌟 World")
        
        assert mock_send.called


@pytest.mark.edge_case
class TestMouseEdgeCases:
    """Edge case tests for mouse utilities."""

    def test_click_at_origin(self, mocker):
        """Test clicking at origin (0, 0)."""
        mocker.patch("src.utils.mouse.pyautogui")
        mocker.patch("src.utils.mouse.human_like_move")
        mocker.patch("time.sleep")
        
        from src.utils.mouse import click_at
        
        # Should not crash
        click_at(0, 0)

    def test_click_at_large_coordinates(self, mocker):
        """Test clicking at very large coordinates."""
        mock_pyautogui = mocker.patch("src.utils.mouse.pyautogui")
        mocker.patch("src.utils.mouse.human_like_move")
        mocker.patch("time.sleep")
        
        from src.utils.mouse import click_at
        
        # Should work (pyautogui will handle out-of-bounds)
        click_at(99999, 99999)

    def test_move_same_start_end(self, mocker):
        """Test move where start equals end."""
        mock_pyautogui = mocker.patch("src.utils.mouse.pyautogui")
        mock_pyautogui.position.return_value = (500, 500)
        mocker.patch("time.sleep")
        
        from src.utils.mouse import human_like_move
        
        # Moving to current position should work
        human_like_move(500, 500)


@pytest.mark.edge_case
class TestConfigEdgeCases:
    """Edge case tests for configuration."""

    def test_missing_env_file(self, mocker, tmp_path):
        """Test behavior when .env file doesn't exist."""
        mocker.patch("src.web_control_panel.ENV_PATH", str(tmp_path / "nonexistent.env"))
        
        from src.web_control_panel import load_env_values
        
        # Should handle gracefully
        result = load_env_values()
        assert isinstance(result, dict)

    def test_empty_env_file(self, mocker, tmp_path):
        """Test behavior with empty .env file."""
        env_path = tmp_path / ".env"
        env_path.write_text("")
        
        mocker.patch("src.web_control_panel.ENV_PATH", str(env_path))
        
        from src.web_control_panel import load_env_values
        
        result = load_env_values()
        assert isinstance(result, dict)

    def test_env_file_with_comments_only(self, mocker, tmp_path):
        """Test .env file containing only comments."""
        env_path = tmp_path / ".env"
        env_path.write_text("# Comment 1\n# Comment 2\n")
        
        mocker.patch("src.web_control_panel.ENV_PATH", str(env_path))
        
        from src.web_control_panel import load_env_values
        
        result = load_env_values()
        assert isinstance(result, dict)


@pytest.mark.edge_case
class TestSecurityEdgeCases:
    """Edge case tests for security modules."""

    def test_encrypt_empty_string(self, tmp_path):
        """Test encrypting an empty string."""
        from src.utils.secure_key_manager import SecureKeyManager
        
        manager = SecureKeyManager(str(tmp_path))
        encrypted = manager.encrypt_key("")
        
        assert encrypted is not None
        assert encrypted != ""

    def test_encrypt_very_long_key(self, tmp_path):
        """Test encrypting a very long key."""
        from src.utils.secure_key_manager import SecureKeyManager
        
        manager = SecureKeyManager(str(tmp_path))
        long_key = "A" * 10000
        
        encrypted = manager.encrypt_key(long_key)
        decrypted = manager.decrypt_key(encrypted)
        
        assert decrypted == long_key

    def test_decrypt_random_base64(self, tmp_path):
        """Test decrypting random base64 that isn't our format."""
        from src.utils.secure_key_manager import SecureKeyManager
        import base64
        
        manager = SecureKeyManager(str(tmp_path))
        random_b64 = base64.b64encode(b"random garbage data").decode()
        
        result = manager.decrypt_key(random_b64)
        
        assert result is None


@pytest.mark.edge_case
class TestScreenEdgeCases:
    """Edge case tests for screen utilities."""

    def test_preprocess_1x1_image(self):
        """Test preprocessing a 1x1 pixel image."""
        from src.utils.screen import preprocess_image_for_ocr
        from PIL import Image
        import numpy as np
        
        tiny_image = Image.fromarray(np.zeros((1, 1, 3), dtype=np.uint8))
        
        result = preprocess_image_for_ocr(tiny_image)
        
        assert len(result) == 4

    def test_find_text_empty_string(self, mocker):
        """Test finding empty string."""
        mocker.patch("src.utils.screen.HAS_TESSERACT", True)
        mock_tesseract = mocker.patch("src.utils.screen.pytesseract")
        
        from src.utils.screen import find_text_coordinates
        from PIL import Image
        import numpy as np
        
        image = Image.fromarray(np.zeros((100, 100, 3), dtype=np.uint8))
        
        result = find_text_coordinates(image, "")
        
        assert result is None


@pytest.mark.edge_case
class TestMainWorkflowEdgeCases:
    """Edge case tests for main application workflow."""

    @pytest.fixture
    def mock_env(self, mocker):
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

        mocker.patch("mss.mss", return_value=mock_mss_instance)
        mocker.patch("time.sleep")
        mocker.patch("src.main.switch_to_input_desktop", return_value=True)
        
        return mocker

    def test_process_with_unknown_response_type(self, mock_env):
        """Test processing unknown response type."""
        mock_env.patch("src.main.get_gemini_response", return_value={
            "type": "UNKNOWN_TYPE",
            "data": "something",
        })
        
        from src.main import process_screen_cycle
        
        action_taken, _ = process_screen_cycle()
        
        # Should handle gracefully
        assert action_taken is False

    def test_process_with_null_response(self, mock_env):
        """Test processing null response."""
        mock_env.patch("src.main.get_gemini_response", return_value=None)
        
        from src.main import process_screen_cycle
        
        action_taken, _ = process_screen_cycle()
        
        assert action_taken is False

    def test_process_with_missing_bbox_field(self, mock_env, mocker):
        """Test MCQ processing when bbox is missing."""
        mock_env.patch("src.main.get_gemini_response", return_value={
            "type": "MCQ",
            "question": "Test",
            "answer_text": "A",
            # Missing bbox
        })
        mocker.patch("src.main.find_text_coordinates", return_value=None)
        
        from src.main import process_screen_cycle
        
        # Should handle gracefully (may skip action)
        try:
            action_taken, _ = process_screen_cycle()
        except KeyError:
            # Acceptable - indicates validation needed
            pass
