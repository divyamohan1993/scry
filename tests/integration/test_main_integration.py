"""
Integration Tests for Main Application Flow
=============================================

Tests for the main application workflow including:
- Screen capture → Gemini → Action flow
- MCQ answer selection
- Descriptive answer typing
- Idempotency checks
- Mode switching

Test Coverage:
- process_screen_cycle
- manual_trigger
- Hotkey registration
- Mode toggle
"""

import json
from unittest.mock import MagicMock, patch, call

import pytest


class TestProcessScreenCycleMCQ:
    """Integration tests for MCQ processing flow."""

    @pytest.fixture
    def mock_screen_capture(self, mocker):
        """Mock screen capture."""
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

        return mocker.patch("mss.mss", return_value=mock_mss_instance)

    @pytest.fixture
    def mock_gemini(self, mocker):
        """Mock Gemini response."""
        return mocker.patch("src.main.get_gemini_response")

    @pytest.fixture
    def mock_find_text(self, mocker):
        """Mock OCR text finding."""
        return mocker.patch("src.main.find_text_coordinates")

    @pytest.fixture
    def mock_click(self, mocker):
        """Mock click action."""
        return mocker.patch("src.main.click_at")

    @pytest.fixture
    def mock_desktop(self, mocker):
        """Mock desktop switching."""
        return mocker.patch("src.main.switch_to_input_desktop", return_value=True)

    def test_mcq_with_ocr_success(
        self, mock_screen_capture, mock_gemini, mock_find_text, 
        mock_click, mock_desktop
    ):
        """Test MCQ flow when OCR finds the answer text."""
        from src.main import process_screen_cycle
        
        mock_gemini.return_value = {
            "type": "MCQ",
            "question": "What is 1+1?",
            "answer_text": "2",
            "bbox": [100, 100, 200, 200],
        }
        mock_find_text.return_value = (500, 500)  # OCR found coordinates
        
        action_taken, question_text = process_screen_cycle()
        
        assert action_taken is True
        assert question_text == "What is 1+1?"
        mock_click.assert_called_once_with(500, 500)

    def test_mcq_with_bbox_fallback(
        self, mock_screen_capture, mock_gemini, mock_find_text,
        mock_click, mock_desktop
    ):
        """Test MCQ flow when OCR fails and uses bbox fallback."""
        from src.main import process_screen_cycle
        
        mock_gemini.return_value = {
            "type": "MCQ",
            "question": "Test Question",
            "answer_text": "Answer",
            "bbox": [150, 150, 200, 200],  # [ymin, xmin, ymax, xmax] scaled 0-1000
        }
        mock_find_text.return_value = None  # OCR failed
        
        action_taken, question_text = process_screen_cycle()
        
        assert action_taken is True
        mock_click.assert_called_once()
        
        # Check coordinates are calculated from bbox
        x, y = mock_click.call_args[0]
        assert 0 <= x <= 1920
        assert 0 <= y <= 1080

    def test_mcq_idempotency_check(
        self, mock_screen_capture, mock_gemini, mock_find_text,
        mock_click, mock_desktop
    ):
        """Test that same question is not processed twice."""
        from src import main
        from src.main import process_screen_cycle
        
        main.last_processed_question = None
        
        mock_gemini.return_value = {
            "type": "MCQ",
            "question": "Repeated Question",
            "answer_text": "A",
            "bbox": [0, 0, 100, 100],
        }
        mock_find_text.return_value = (100, 100)
        
        # First call
        process_screen_cycle()
        assert mock_click.call_count == 1
        
        # Second call - same question
        process_screen_cycle()
        assert mock_click.call_count == 1  # Should NOT increase
        
        # Third call with bypass
        process_screen_cycle(bypass_idempotency=True)
        assert mock_click.call_count == 2  # Should increase


class TestProcessScreenCycleDescriptive:
    """Integration tests for descriptive answer processing."""

    @pytest.fixture
    def mock_screen_capture(self, mocker):
        """Mock screen capture."""
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

        return mocker.patch("mss.mss", return_value=mock_mss_instance)

    @pytest.fixture
    def mock_gemini(self, mocker):
        """Mock Gemini response."""
        return mocker.patch("src.main.get_gemini_response")

    @pytest.fixture
    def mock_type_text(self, mocker):
        """Mock typing function."""
        return mocker.patch("src.main.type_text_human_like")

    @pytest.fixture
    def mock_desktop(self, mocker):
        """Mock desktop switching."""
        return mocker.patch("src.main.switch_to_input_desktop", return_value=True)

    def test_descriptive_answer_flow(
        self, mock_screen_capture, mock_gemini, mock_type_text, mock_desktop
    ):
        """Test descriptive answer typing flow."""
        from src.main import process_screen_cycle
        
        mock_gemini.return_value = {
            "type": "DESCRIPTIVE",
            "question": "Explain photosynthesis",
            "answer_text": "Photosynthesis is the process by which plants convert sunlight into energy.",
            "marks": 5,
        }
        
        action_taken, question_text = process_screen_cycle()
        
        assert action_taken is True
        assert question_text == "Explain photosynthesis"
        mock_type_text.assert_called_once()
        
        # Verify the answer was typed
        typed_text = mock_type_text.call_args[0][0]
        assert "Photosynthesis" in typed_text


class TestProcessScreenCycleSafe:
    """Integration tests for SAFE response handling."""

    @pytest.fixture
    def mock_screen_capture(self, mocker):
        """Mock screen capture."""
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

        return mocker.patch("mss.mss", return_value=mock_mss_instance)

    @pytest.fixture
    def mock_gemini(self, mocker):
        """Mock Gemini response."""
        return mocker.patch("src.main.get_gemini_response")

    @pytest.fixture
    def mock_click(self, mocker):
        """Mock click action."""
        return mocker.patch("src.main.click_at")

    @pytest.fixture
    def mock_type_text(self, mocker):
        """Mock typing function."""
        return mocker.patch("src.main.type_text_human_like")

    def test_safe_response_no_action(
        self, mock_screen_capture, mock_gemini, mock_click, mock_type_text
    ):
        """Test that SAFE response takes no action."""
        from src.main import process_screen_cycle
        
        mock_gemini.return_value = {
            "type": "SAFE",
        }
        
        action_taken, question_text = process_screen_cycle()
        
        assert action_taken is False
        mock_click.assert_not_called()
        mock_type_text.assert_not_called()


class TestManualTrigger:
    """Integration tests for manual hotkey triggers."""

    @pytest.fixture
    def mock_all(self, mocker):
        """Mock all required components."""
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

    def test_manual_mcq_trigger(self, mock_all):
        """Test manual MCQ trigger."""
        from src.main import manual_trigger
        
        mock_all["gemini"].return_value = {
            "type": "MCQ",
            "question": "Manual Test",
            "answer_text": "A",
            "bbox": [0, 0, 100, 100],
        }
        mock_all["find_text"].return_value = (50, 50)
        
        manual_trigger("MCQ")
        
        mock_all["click"].assert_called()

    def test_manual_descriptive_trigger(self, mock_all, mocker):
        """Test manual descriptive trigger."""
        mock_type = mocker.patch("src.main.type_text_human_like")
        
        from src.main import manual_trigger
        
        mock_all["gemini"].return_value = {
            "type": "DESCRIPTIVE",
            "question": "Manual Descriptive",
            "answer_text": "This is the answer.",
        }
        
        manual_trigger("DESCRIPTIVE")
        
        mock_type.assert_called()


class TestModeToggle:
    """Integration tests for mode toggling."""

    def test_toggle_mode_changes_state(self, mocker):
        """Test that toggle_mode changes the mode state."""
        mocker.patch("src.runtime_config.get_config", return_value=False)
        
        from src import main
        
        initial_mode = main.is_manual_mode
        main.toggle_mode()
        
        assert main.is_manual_mode != initial_mode


class TestErrorHandling:
    """Integration tests for error handling scenarios."""

    def test_gemini_returns_none(self, mocker):
        """Test handling when Gemini returns None."""
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
        mocker.patch("src.main.get_gemini_response", return_value=None)
        
        from src.main import process_screen_cycle
        
        action_taken, q_text = process_screen_cycle()
        
        assert action_taken is False

    def test_gemini_returns_empty_dict(self, mocker):
        """Test handling when Gemini returns empty dict."""
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
        mocker.patch("src.main.get_gemini_response", return_value={})
        
        from src.main import process_screen_cycle
        
        action_taken, q_text = process_screen_cycle()
        
        assert action_taken is False

    def test_screen_access_denied(self, mocker):
        """Test handling of screen access error."""
        mock_mss = MagicMock()
        mock_mss.__enter__.side_effect = Exception("Screen access denied")
        mocker.patch("mss.mss", return_value=mock_mss)
        
        from src.main import process_screen_cycle
        
        with pytest.raises(Exception, match="Screen access denied"):
            process_screen_cycle()


class TestMultiMCQ:
    """Integration tests for multi-select MCQ processing."""

    @pytest.fixture
    def mock_all(self, mocker):
        """Mock all required components."""
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

    def test_multi_mcq_clicks_multiple_options(self, mock_all):
        """Test that MULTI_MCQ clicks multiple options."""
        from src.main import process_screen_cycle
        
        mock_all["gemini"].return_value = {
            "type": "MULTI_MCQ",
            "question": "Select all correct answers",
            "answers": [
                {"answer_text": "A", "bbox": [100, 100, 150, 150]},
                {"answer_text": "C", "bbox": [200, 100, 250, 150]},
            ],
        }
        
        action_taken, question_text = process_screen_cycle()
        
        assert action_taken is True
        # Should click twice (once for each answer)
        assert mock_all["click"].call_count == 2
