import os
import sys
import unittest
from unittest.mock import ANY, MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import src modules (ensure they are available)
try:
    from src import main
except ImportError:
    # If run heavily nested, adjust path
    pass


class TestStrictSimulation(unittest.TestCase):
    def setUp(self):
        # Disable Main Logger during tests to keep output clean,
        # or mock it to verify logs if needed.
        self.mock_logger_patcher = patch("src.main.logger")
        self.mock_logger = self.mock_logger_patcher.start()

    def tearDown(self):
        self.mock_logger_patcher.stop()

    @patch("src.main.mss.mss")
    @patch("src.main.get_gemini_response")
    @patch("src.main.find_text_coordinates")
    @patch("src.main.click_at")
    @patch("src.main.switch_to_input_desktop")
    def test_mcq_happy_path(
        self, mock_switch, mock_click, mock_find, mock_gemini, mock_mss
    ):
        """
        [SIMULATION] MCQ Happy Path
        Situation: Perfect network, perfect OCR, valid coordinates.
        Expected: Click at exact coordinates.
        """
        # 1. Setup Data
        mock_switch.return_value = True

        # Mock MSS
        mock_sct_instance = MagicMock()
        mock_mss.return_value.__enter__.return_value = mock_sct_instance
        monitor = {"top": 0, "left": 0, "width": 1920, "height": 1080}
        mock_sct_instance.monitors = [None, monitor]

        mock_grab = MagicMock()
        mock_grab.size = (1920, 1080)
        mock_grab.bgra = b"\x00" * (1920 * 1080 * 4)
        mock_sct_instance.grab.return_value = mock_grab

        # 2. Mock Gemini Response (Strict Schema)
        mock_gemini.return_value = {
            "type": "MCQ",
            "question": "What is the capital of France?",
            "answer_text": "Paris",
            "bbox": [100, 100, 200, 300],
        }

        # 3. Mock OCR finding text
        # find_text_coordinates returns relative (x, y) in the screenshot
        mock_find.return_value = (500, 500)

        # 4. Run Function
        action_taken, q = main.process_screen_cycle(
            mode_hint="MCQ", bypass_idempotency=True
        )

        # 5. Validation
        self.assertTrue(action_taken, "Action should be taken for valid MCQ")
        self.assertEqual(q, "What is the capital of France?")

        # Verify Click Coordinates:
        # Logic is: final_x = x + monitor["left"]
        # (500 + 0, 500 + 0) = (500, 500)
        mock_click.assert_called_once_with(500, 500)

        # Verify Switch to Desktop was called (essential for hidden screens)
        mock_switch.assert_called_once()

    @patch("src.main.mss.mss")
    @patch("src.main.get_gemini_response")
    @patch("src.main.find_text_coordinates")
    @patch("src.main.click_at")
    def test_mcq_failsafe_path(self, mock_click, mock_find, mock_gemini, mock_mss):
        """
        [SIMULATION] MCQ Failsafe Path
        Situation: OCR fails to find text (returns None).
        Expected: Fallback to Gemini Bounding Box.
        """
        # Mock Failure of OCR
        mock_find.return_value = None

        # MSS
        mock_sct_instance = MagicMock()
        mock_mss.return_value.__enter__.return_value = mock_sct_instance
        monitor = {"top": 100, "left": 100, "width": 1000, "height": 1000}
        mock_sct_instance.monitors = [None, monitor]
        mock_grab = MagicMock()
        mock_grab.size = (1000, 1000)
        mock_grab.bgra = b"\x00" * (1000 * 1000 * 4)
        mock_sct_instance.grab.return_value = mock_grab

        # Mock Gemini
        # Box is typically [ymin, xmin, ymax, xmax] in 0-1000 scale
        # Let's target center 500, 500 relative to width/height
        # Bbox for center 500,500 would be e.g. [450, 450, 550, 550]
        mock_gemini.return_value = {
            "type": "MCQ",
            "question": "Failsafe Question",
            "answer_text": "Invisible Option",
            "bbox": [400, 400, 600, 600],
        }

        # Run
        action_taken, _ = main.process_screen_cycle(bypass_idempotency=True)

        # Check
        self.assertTrue(action_taken)

        # Expected calculation:
        # Center Scale X = (400+600)/2 = 500. 500/1000 = 0.5. 0.5 * 1000 = 500.
        # Global X = 500 + Left(100) = 600.
        # Global Y = 500 + Top(100) = 600.
        mock_click.assert_called_once_with(600, 600)

    @patch("src.main.mss.mss")
    @patch("src.main.get_gemini_response")
    @patch("src.main.type_text_human_like")
    @patch("src.main.switch_to_input_desktop")
    def test_descriptive_mode(self, mock_switch, mock_type, mock_gemini, mock_mss):
        """
        [SIMULATION] Descriptive Answer
        Situation: 'DESCRIPTIVE' type returned.
        Expected: Type text human-like.
        """
        mock_switch.return_value = True

        # MSS
        mock_sct_instance = MagicMock()
        mock_mss.return_value.__enter__.return_value = mock_sct_instance
        mock_sct_instance.monitors = [
            None,
            {"top": 0, "left": 0, "width": 100, "height": 100},
        ]
        mock_grab = MagicMock()
        mock_grab.size = (100, 100)
        mock_grab.bgra = b"\x00" * 40000
        mock_sct_instance.grab.return_value = mock_grab

        # Mock Gemini
        mock_gemini.return_value = {
            "type": "DESCRIPTIVE",
            "question": "Explain things.",
            "answer_text": "This is a detailed explanation.",
            "marks": 5,
        }

        # Enable detailed mode logic
        with patch("src.main.ENABLE_DETAILED_MODE", True):
            action_taken, _ = main.process_screen_cycle(
                mode_hint="DESCRIPTIVE", bypass_idempotency=True
            )

        self.assertTrue(action_taken)
        mock_type.assert_called_once_with(
            "This is a detailed explanation.", min_wpm=ANY, max_wpm=ANY
        )


if __name__ == "__main__":
    print("Running Strict Simulation Suite...")
    unittest.main()
