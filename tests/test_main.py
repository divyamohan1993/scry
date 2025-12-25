from unittest.mock import MagicMock

import pytest

from src import main
from src.main import manual_trigger, process_screen_cycle


class TestMainProcessCycle:

    @pytest.fixture
    def mock_screen_capture(self, mocker):
        # Mock mss.mss() context manager
        mock_mss_instance = MagicMock()
        mock_enter = MagicMock()
        mock_mss_instance.__enter__.return_value = mock_enter

        # Mock screen grab return
        mock_sct_img = MagicMock()
        mock_sct_img.size = (1920, 1080)
        mock_sct_img.bgra = b"\x00" * (1920 * 1080 * 4)  # dummy data
        mock_enter.grab.return_value = mock_sct_img
        mock_enter.monitors = [{}, {"left": 0, "top": 0, "width": 1920, "height": 1080}]

        return mocker.patch("mss.mss", return_value=mock_mss_instance)

    @pytest.fixture
    def mock_gemini(self, mocker):
        return mocker.patch("src.main.get_gemini_response")

    @pytest.fixture
    def mock_find_text(self, mocker):
        return mocker.patch("src.main.find_text_coordinates")

    @pytest.fixture
    def mock_click(self, mocker):
        return mocker.patch("src.main.click_at")

    @pytest.fixture
    def mock_type_text(self, mocker):
        return mocker.patch("src.main.type_text_human_like")

    @pytest.fixture
    def mock_desktop(self, mocker):
        return mocker.patch("src.main.switch_to_input_desktop", return_value=True)

    def test_mcq_success_ocr_match(
        self, mock_screen_capture, mock_gemini, mock_find_text, mock_click, mock_desktop
    ):
        """Test standard MCQ flow where OCR finds the text."""
        # Setup
        mock_gemini.return_value = {
            "type": "MCQ",
            "question": "Q1",
            "answer_text": "Choice A",
            "bbox": [10, 10, 20, 20],
        }
        mock_find_text.return_value = (500, 500)  # x, y found by OCR

        # Execute
        action_taken, question_text = process_screen_cycle()

        # Verify
        assert action_taken is True
        assert question_text == "Q1"
        mock_click.assert_called_once_with(
            500, 500
        )  # Should click OCR coords + monitor offset (0,0 here)

    def test_mcq_failsafe_fallback(
        self, mock_screen_capture, mock_gemini, mock_find_text, mock_click, mock_desktop
    ):
        """Test MCQ flow where OCR fails but BBox fallback works."""
        # Setup
        mock_gemini.return_value = {
            "type": "MCQ",
            "question": "Q2",
            "answer_text": "Choice B",
            # bbox is [ymin, xmin, ymax, xmax] scaled 0-1000
            "bbox": [100, 100, 200, 200],
        }
        mock_find_text.return_value = None  # OCR failed

        # Execute
        action_taken, question_text = process_screen_cycle()

        # Verify
        assert action_taken is True
        # Calculate expected center
        # xmin=100, xmax=200 -> center_x = 150/1000 * 1920 = 288
        # ymin=100, ymax=200 -> center_y = 150/1000 * 1080 = 162
        mock_click.assert_called_once()
        args = mock_click.call_args[0]
        assert 280 <= args[0] <= 295  # approximate check
        assert 155 <= args[1] <= 170

    def test_descriptive_success(
        self, mock_screen_capture, mock_gemini, mock_type_text, mock_desktop
    ):
        """Test Descriptive question flow."""
        # Setup
        mock_gemini.return_value = {
            "type": "DESCRIPTIVE",
            "question": "Write an essay.",
            "answer_text": "This is an essay.",
            "marks": 5,
        }

        # Execute
        action_taken, question_text = process_screen_cycle()

        # Verify
        assert action_taken is True
        mock_type_text.assert_called_once()
        assert "This is an essay." in mock_type_text.call_args[0][0]

    def test_idempotency_check(
        self, mock_screen_capture, mock_gemini, mock_find_text, mock_click
    ):
        """Test that the same question is not processed twice consecutively."""
        # Reset state
        main.last_processed_question = None

        mock_gemini.return_value = {
            "type": "MCQ",
            "question": "Repeated Q",
            "answer_text": "A",
            "bbox": [0, 0, 10, 10],
        }
        mock_find_text.return_value = (100, 100)

        # First pass
        process_screen_cycle()
        assert mock_click.call_count == 1

        # Second pass (same internal state)
        process_screen_cycle()
        assert mock_click.call_count == 1  # Should NOT increase

        # Third pass (bypass_idempotency=True)
        process_screen_cycle(bypass_idempotency=True)
        assert mock_click.call_count == 2  # Should increase

    def test_empty_gemini_response(self, mock_screen_capture, mock_gemini):
        """Test handling of None/empty response from Gemini."""
        mock_gemini.return_value = None
        action, q_text = process_screen_cycle()
        assert action is False

        mock_gemini.return_value = {}
        action, q_text = process_screen_cycle()
        assert action is False

    def test_manual_trigger(
        self, mocker, mock_screen_capture, mock_gemini, mock_find_text, mock_click
    ):
        """Test manual trigger flow."""
        # Mock time.sleep to run fast
        mocker.patch("time.sleep")

        mock_gemini.return_value = {
            "type": "MCQ",
            "question": "Manual Q",
            "answer_text": "A",
            "bbox": [0, 0, 1, 1],
        }
        mock_find_text.return_value = (50, 50)

        manual_trigger("MCQ")

        # Verify it called process_screen_cycle with bypass_idempotency=True
        # (Though we can verify the outcome: click happened)
        mock_click.assert_called_once()

    def test_monitor_access_error(self, mocker, mock_gemini):
        """Strict fail check: MSS fails to grab screen."""
        mock_mss_fail = MagicMock()
        mock_mss_fail.__enter__.side_effect = Exception("Screen access denied")
        mocker.patch("mss.mss", return_value=mock_mss_fail)

        with pytest.raises(Exception) as excinfo:
            process_screen_cycle()
        assert "Screen access denied" in str(excinfo.value)
