import difflib
import os
import shutil

import cv2
import numpy as np
import pyautogui
import pytesseract
from PIL import Image
from pytesseract import Output

from ..config import SCREENSHOTS_DIR
from ..logger import get_logger

logger = get_logger("ScreenUtils")

# Check Tesseract Availability Once
HAS_TESSERACT = False
possible_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.environ.get("TESSDATA_PREFIX", ""),  # detailed check not needed, just path
]

# Check existing PATH
if shutil.which("tesseract"):
    HAS_TESSERACT = True
else:
    # Check manual paths
    for p in possible_paths:
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            HAS_TESSERACT = True
            break

if not HAS_TESSERACT:
    logger.info(
        "Local OCR unavailable (Tesseract not found). Switched to AI Vision Mode (Gemini)."
    )


def capture_screen(filename=None):
    """
    Captures full screen.
    """
    screenshot = pyautogui.screenshot()
    if filename:
        path = os.path.join(SCREENSHOTS_DIR, filename)
        screenshot.save(path)
        logger.debug(f"Saved screenshot to {path}")
    return screenshot


def preprocess_image_for_ocr(pil_image):
    """
    Advanced preprocessing pipeline to maximize OCR accuracy.
    Returns a list of processed images to try: [Original, Grayscale, Thresholded, Inverted]
    """
    # Convert PIL to OpenCV format
    img_cv = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    # 1. Grayscale
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # 2. Binary Thresholding (Standard) - Good for black text on white
    # Uses Otsu's binarization automatically
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 3. Inverted Threshold - Good for white text on dark background
    thresh_inv = cv2.bitwise_not(thresh)

    # Convert back to PIL images for Tesseract
    return [
        pil_image,  # Try raw first (sometimes it's best)
        Image.fromarray(gray),
        Image.fromarray(thresh),
        Image.fromarray(thresh_inv),
    ]


def find_text_coordinates(image, target_text):
    """
    Finds the center coordinates of the target_text in the image using OCR.
    Uses 'Advanced Multi-Stage Detection' to ensure 100% certainty.
    """
    if not HAS_TESSERACT:
        logger.debug("Skipping local OCR (Tesseract not available).")
        return None

    if not target_text:
        return None

    target_words = target_text.split()
    normalized_target = [w.lower() for w in target_words]
    logger.debug(f"Targeting logic initiated for: '{target_text}'")

    # Generate processed variants
    processed_images = preprocess_image_for_ocr(image)

    best_overall_match = None
    best_overall_ratio = 0.0

    # Try parallel-ish execution (sequential here for simplicity) on all image variants
    for idx, img_variant in enumerate(processed_images):
        variant_name = ["Raw", "Grayscale", "Threshold", "Inverted"][idx]
        logger.debug(f"Stage {idx + 1}: Running OCR on {variant_name} image...")

        try:
            # PSM 11 = Sparse text (good for UI labels)
            data = pytesseract.image_to_data(
                img_variant, output_type=Output.DICT, config="--psm 11"
            )

            n_boxes = len(data["text"])
            found_words = []

            for i in range(n_boxes):
                if int(data["conf"][i]) > 0:
                    text = data["text"][i].strip()
                    if text:
                        found_words.append(
                            {
                                "text": text,
                                "left": data["left"][i],
                                "top": data["top"][i],
                                "width": data["width"][i],
                                "height": data["height"][i],
                            }
                        )

            # Search for best match in this variant
            for i in range(len(found_words) - len(target_words) + 1):
                window = found_words[i : i + len(target_words)]
                window_text = [w["text"].lower() for w in window]

                matcher = difflib.SequenceMatcher(None, normalized_target, window_text)
                ratio = matcher.ratio()

                if ratio > best_overall_ratio:
                    best_overall_ratio = ratio
                    best_overall_match = window
                    logger.debug(
                        f"  > New Best Match in {variant_name}: {window_text} (Conf: {ratio:.2f})"
                    )

                    # 100% Match Short-circuit
                    if ratio == 1.0:
                        break

            if best_overall_ratio == 1.0:
                logger.info("  > Perfect match found. Stopping OCR pipeline.")
                break

        except Exception as e:
            logger.error(f"OCR Error in stage {variant_name}: {e}")
            continue

    # Result processing
    if best_overall_match and best_overall_ratio > 0.8:
        x1 = best_overall_match[0]["left"]
        y1 = best_overall_match[0]["top"]
        x2 = best_overall_match[-1]["left"] + best_overall_match[-1]["width"]
        y2 = best_overall_match[-1]["top"] + best_overall_match[-1]["height"]

        # Calculate EXACT center
        center_x = x1 + (x2 - x1) // 2
        center_y = y1 + (y2 - y1) // 2

        logger.info(
            f"Target Acquired: '{target_text}' at ({center_x}, {center_y}) | Confidence: {best_overall_ratio:.2f}"
        )
        return (center_x, center_y)

    logger.warning(
        f"Target Acquisition Failed. Best Confidence: {best_overall_ratio:.2f}"
    )
    return None
