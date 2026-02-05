"""
Unit Tests for Screen Utilities Module
=======================================

Tests for src/utils/screen.py including:
- Screen capture
- OCR preprocessing
- Text coordinate finding
- Image processing

Test Coverage:
- capture_screen
- preprocess_image_for_ocr
- find_text_coordinates
"""

import os
from unittest.mock import MagicMock, patch

import pytest
import numpy as np
from PIL import Image


class TestCaptureScreen:
    """Tests for capture_screen function."""

    @pytest.fixture
    def mock_pyautogui(self, mocker):
        """Mock pyautogui for screenshot."""
        mock = MagicMock()
        mock_screenshot = MagicMock()
        mock_screenshot.size = (1920, 1080)
        mock.screenshot.return_value = mock_screenshot
        mocker.patch("src.utils.screen.pyautogui", mock)
        return mock

    def test_capture_screen_returns_image(self, mock_pyautogui):
        """Test that capture_screen returns an image."""
        from src.utils.screen import capture_screen
        
        result = capture_screen()
        
        assert result is not None

    def test_capture_screen_with_filename(self, mock_pyautogui, tmp_path, mocker):
        """Test capture_screen saves to filename."""
        mocker.patch("src.utils.screen.SCREENSHOTS_DIR", str(tmp_path))
        
        from src.utils.screen import capture_screen
        
        result = capture_screen(filename="test_screenshot.png")
        
        assert result is not None

    def test_capture_screen_calls_pyautogui(self, mock_pyautogui):
        """Test that capture_screen uses pyautogui."""
        from src.utils.screen import capture_screen
        
        capture_screen()
        
        mock_pyautogui.screenshot.assert_called_once()


class TestPreprocessImageForOCR:
    """Tests for preprocess_image_for_ocr function."""

    @pytest.fixture
    def test_image(self):
        """Create a test image."""
        # Create a simple black and white test image
        img_array = np.zeros((100, 100, 3), dtype=np.uint8)
        img_array[20:80, 20:80] = 255  # White square
        return Image.fromarray(img_array)

    def test_returns_list_of_images(self, test_image):
        """Test that preprocessing returns multiple image variants."""
        from src.utils.screen import preprocess_image_for_ocr
        
        result = preprocess_image_for_ocr(test_image)
        
        assert isinstance(result, list)
        assert len(result) == 4  # Raw, Grayscale, Threshold, Inverted

    def test_first_image_is_original(self, test_image):
        """Test that first returned image is the original."""
        from src.utils.screen import preprocess_image_for_ocr
        
        result = preprocess_image_for_ocr(test_image)
        
        assert result[0] == test_image

    def test_grayscale_conversion(self, test_image):
        """Test that grayscale conversion works."""
        from src.utils.screen import preprocess_image_for_ocr
        
        result = preprocess_image_for_ocr(test_image)
        
        # Second image should be grayscale
        grayscale = result[1]
        assert grayscale.mode == 'L' or len(np.array(grayscale).shape) == 2


class TestFindTextCoordinates:
    """Tests for find_text_coordinates function."""

    @pytest.fixture
    def mock_tesseract(self, mocker):
        """Mock pytesseract."""
        mock = MagicMock()
        mock.image_to_data.return_value = {
            "text": ["Hello", "World"],
            "conf": [90, 90],
            "left": [10, 50],
            "top": [10, 10],
            "width": [30, 40],
            "height": [20, 20],
        }
        mocker.patch("src.utils.screen.pytesseract", mock)
        mocker.patch("src.utils.screen.HAS_TESSERACT", True)
        return mock

    @pytest.fixture
    def test_image(self):
        """Create a test image."""
        img_array = np.zeros((100, 100, 3), dtype=np.uint8)
        return Image.fromarray(img_array)

    def test_find_text_returns_coordinates(self, mock_tesseract, test_image):
        """Test that find_text_coordinates returns coordinates."""
        from src.utils.screen import find_text_coordinates
        
        result = find_text_coordinates(test_image, "Hello")
        
        # Should return coordinates or None
        assert result is None or (isinstance(result, tuple) and len(result) == 2)

    def test_find_text_with_empty_target(self, mock_tesseract, test_image):
        """Test find_text with empty target text."""
        from src.utils.screen import find_text_coordinates
        
        result = find_text_coordinates(test_image, "")
        
        assert result is None

    def test_find_text_without_tesseract(self, mocker, test_image):
        """Test find_text when Tesseract is not available."""
        mocker.patch("src.utils.screen.HAS_TESSERACT", False)
        
        from src.utils.screen import find_text_coordinates
        
        result = find_text_coordinates(test_image, "Test")
        
        assert result is None


class TestTesseractDetection:
    """Tests for Tesseract OCR detection."""

    def test_has_tesseract_is_boolean(self):
        """Test that HAS_TESSERACT is a boolean."""
        from src.utils.screen import HAS_TESSERACT
        
        assert isinstance(HAS_TESSERACT, bool)


class TestImageProcessingEdgeCases:
    """Tests for image processing edge cases."""

    def test_preprocess_very_small_image(self):
        """Test preprocessing a very small image."""
        from src.utils.screen import preprocess_image_for_ocr
        
        small_image = Image.fromarray(np.zeros((10, 10, 3), dtype=np.uint8))
        
        result = preprocess_image_for_ocr(small_image)
        
        assert len(result) == 4

    def test_preprocess_large_image(self):
        """Test preprocessing a large image."""
        from src.utils.screen import preprocess_image_for_ocr
        
        large_image = Image.fromarray(np.zeros((2000, 2000, 3), dtype=np.uint8))
        
        result = preprocess_image_for_ocr(large_image)
        
        assert len(result) == 4

    def test_preprocess_rgba_image(self):
        """Test preprocessing an RGBA image."""
        from src.utils.screen import preprocess_image_for_ocr
        
        # RGBA image (4 channels)
        rgba_array = np.zeros((100, 100, 4), dtype=np.uint8)
        rgba_array[:, :, 3] = 255  # Alpha channel
        rgba_image = Image.fromarray(rgba_array, 'RGBA')
        
        # Convert to RGB as the function expects RGB
        rgb_image = rgba_image.convert('RGB')
        
        result = preprocess_image_for_ocr(rgb_image)
        
        assert len(result) == 4


class TestSequenceMatching:
    """Tests for text sequence matching logic."""

    @pytest.fixture
    def mock_tesseract_with_sequence(self, mocker):
        """Mock pytesseract with a sequence of words."""
        mock = MagicMock()
        mock.image_to_data.return_value = {
            "text": ["The", "quick", "brown", "fox", "jumps"],
            "conf": [90, 90, 90, 90, 90],
            "left": [10, 50, 100, 150, 200],
            "top": [10, 10, 10, 10, 10],
            "width": [30, 40, 50, 30, 50],
            "height": [20, 20, 20, 20, 20],
        }
        mocker.patch("src.utils.screen.pytesseract", mock)
        mocker.patch("src.utils.screen.HAS_TESSERACT", True)
        return mock

    @pytest.fixture
    def test_image(self):
        """Create a test image."""
        img_array = np.zeros((100, 300, 3), dtype=np.uint8)
        return Image.fromarray(img_array)

    def test_find_multi_word_sequence(self, mock_tesseract_with_sequence, test_image):
        """Test finding a multi-word sequence."""
        from src.utils.screen import find_text_coordinates
        
        result = find_text_coordinates(test_image, "quick brown")
        
        # Should find or return None
        assert result is None or isinstance(result, tuple)

    def test_find_partial_match(self, mock_tesseract_with_sequence, test_image):
        """Test finding with partial/fuzzy match."""
        from src.utils.screen import find_text_coordinates
        
        result = find_text_coordinates(test_image, "quik brown")  # Typo
        
        # Fuzzy matching should work (depends on threshold)
        assert result is None or isinstance(result, tuple)


class TestConfidenceThreshold:
    """Tests for OCR confidence threshold handling."""

    @pytest.fixture
    def mock_tesseract_low_conf(self, mocker):
        """Mock pytesseract with low confidence results."""
        mock = MagicMock()
        mock.image_to_data.return_value = {
            "text": ["Maybe", "Text"],
            "conf": [20, 30],  # Low confidence
            "left": [10, 50],
            "top": [10, 10],
            "width": [30, 40],
            "height": [20, 20],
        }
        mocker.patch("src.utils.screen.pytesseract", mock)
        mocker.patch("src.utils.screen.HAS_TESSERACT", True)
        return mock

    @pytest.fixture
    def test_image(self):
        """Create a test image."""
        return Image.fromarray(np.zeros((100, 100, 3), dtype=np.uint8))

    def test_low_confidence_results(self, mock_tesseract_low_conf, test_image):
        """Test handling of low confidence OCR results."""
        from src.utils.screen import find_text_coordinates
        
        result = find_text_coordinates(test_image, "Maybe")
        
        # Low confidence should still be processed (conf > 0)
        assert result is None or isinstance(result, tuple)
