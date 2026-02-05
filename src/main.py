import sys
import time
import traceback
import random

import mss
import pyautogui
from PIL import Image

try:
    import keyboard
except ImportError:
    print(
        "Error: 'keyboard' library not found. Please install it with 'pip install keyboard'."
    )
    sys.exit(1)

import os
import atexit
from .config import (
    DEV_MAX_ITERATIONS,
    DEV_SAVE_SCREENSHOTS,
    DEVELOPER_MODE,
    ENABLE_DETAILED_MODE,
    HOTKEY_DELAY,
    HOTKEY_DESCRIPTIVE,
    HOTKEY_MCQ,
    HOTKEY_CLIPBOARD,
    HOTKEY_MULTI_MCQ,
    HOTKEY_TOGGLE_MODE,
    INITIAL_WAIT,
    MANUAL_MODE,
    POLL_INTERVAL,
    POST_ACTION_WAIT,
    SCREENSHOTS_DIR,
    RUNTIME_DIR,
    TYPING_WPM_MAX,
    TYPING_WPM_MIN,
    UPDATE_CHECK_INTERVAL_SECONDS,
    REQUIRE_LICENSE,
    validate_license,
)
from .gemini import get_gemini_response
from .logger import get_logger
from .utils.desktop_manager import switch_to_input_desktop, type_text_human_like
from .utils.mouse import click_at, move_away_from_options, simulate_reading_pause, reset_fatigue
from .utils.screen import find_text_coordinates
from .updater import check_and_update

logger = get_logger("Main")


# State Variables
last_processed_question = None

# =============================================================================
# RUNTIME MODE STATE (can be toggled at runtime)
# =============================================================================
# This is the runtime state that can be changed while the app is running
# It starts with the value from config but can be toggled via hotkey
is_manual_mode = MANUAL_MODE


def toggle_mode():
    """
    Toggle between MANUAL and AUTO modes at runtime.
    Called when the mode toggle hotkey is pressed.
    """
    global is_manual_mode
    is_manual_mode = not is_manual_mode
    
    mode_name = "MANUAL (Hotkeys Only)" if is_manual_mode else "AUTO (Loop)"
    logger.info(f"MODE SWITCHED to: {mode_name}")
    
    if is_manual_mode:
        logger.info("Now in MANUAL MODE - Only hotkey triggers will work.")
        logger.info("Multi-Select MCQ is available in MANUAL mode only.")
    else:
        logger.info("Now in AUTO MODE - Screen polling active.")
        logger.info("MCQ and Descriptive questions will be auto-detected.")
        logger.info("Note: Multi-Select MCQ is NOT available in AUTO mode.")


def log_current_mode_info():
    """Log information about available hotkeys and current mode."""
    logger.info(f"Press '{HOTKEY_MCQ}' THREE TIMES for MCQ search.")
    if is_manual_mode:
        logger.info(f"Press '{HOTKEY_MULTI_MCQ}' THREE TIMES for Multi-Select MCQ search.")
    logger.info(f"Press '{HOTKEY_DESCRIPTIVE}' THREE TIMES for Descriptive search.")
    logger.info(f"Press '{HOTKEY_CLIPBOARD}' THREE TIMES for Clipboard Stream.")
    logger.info(f"Press '{HOTKEY_TOGGLE_MODE}' THREE TIMES to toggle MANUAL/AUTO mode.")
    logger.info("Note: Any other key press between the 3 presses will reset the count.")


# =============================================================================
# TRIPLE-PRESS HOTKEY TRACKER
# =============================================================================
class TriplePressTracker:
    """
    Tracks consecutive key presses and triggers actions only when
    a key is pressed 3 times in succession.
    
    Rules:
    - A key must be pressed 3 times consecutively to trigger its action
    - If any other key is pressed between the 3 presses, the count resets
    - There is NO time limit between presses (can be seconds, minutes, etc.)
    - The count only resets when a DIFFERENT key is pressed
    """
    
    def __init__(self):
        self.last_key = None
        self.press_count = 0
        self.hotkey_actions = {}  # Maps key -> action function
        self.registered_keys = set()  # Keys we're tracking
    
    def register_hotkey(self, key: str, action):
        """
        Register a hotkey with its associated action.
        The action will only be triggered on 3 consecutive presses.
        """
        key_lower = key.lower()
        self.hotkey_actions[key_lower] = action
        self.registered_keys.add(key_lower)
        logger.debug(f"Registered triple-press hotkey: '{key}' (press 3x to trigger)")
    
    def on_key_press(self, event):
        """
        Called on every key press. Tracks consecutive presses
        and triggers action when count reaches 3.
        """
        key_name = event.name.lower() if hasattr(event, 'name') else str(event).lower()
        
        # Check if this is a registered hotkey
        if key_name in self.registered_keys:
            if key_name == self.last_key:
                # Same key pressed again - increment count
                self.press_count += 1
                logger.debug(f"Hotkey '{key_name}' pressed {self.press_count}/3")
                
                if self.press_count >= 3:
                    # Triple press achieved! Trigger the action
                    logger.info(f"Triple-press detected for '{key_name}' - triggering action!")
                    self.press_count = 0
                    self.last_key = None
                    
                    # Execute the action
                    action = self.hotkey_actions.get(key_name)
                    if action:
                        try:
                            action()
                        except Exception as e:
                            logger.error(f"Error executing hotkey action: {e}")
            else:
                # Different registered key - start new count
                self.last_key = key_name
                self.press_count = 1
                logger.debug(f"Hotkey '{key_name}' pressed 1/3")
        else:
            # Non-registered key pressed - reset tracking
            if self.press_count > 0:
                logger.debug(f"Non-hotkey '{key_name}' pressed - resetting count")
            self.last_key = None
            self.press_count = 0


# Global tracker instance
triple_press_tracker = TriplePressTracker()

def create_pid_file():
    """Creates a PID file for the current process."""
    pid_path = os.path.join(RUNTIME_DIR, "app.pid")
    try:
        with open(pid_path, "w") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        logger.error(f"Failed to create PID file: {e}")

def remove_pid_file():
    """Removes the PID file on exit."""
    pid_path = os.path.join(RUNTIME_DIR, "app.pid")
    if os.path.exists(pid_path):
        try:
            os.remove(pid_path)
        except Exception:
            pass



def process_screen_cycle(mode_hint=None, bypass_idempotency=False):
    """
    Captures screen, sends to Gemini, and acts on it.
    mode_hint: 'MCQ' or 'DESCRIPTIVE' (or None)
    bypass_idempotency: If True, ignores whether the question was seen before.
    Returns: (bool action_taken, str question_text)
    """
    global last_processed_question

    # 0. Ensure we are on the active desktop
    if not switch_to_input_desktop():
        logger.warning(
            "Could not switch to input desktop. Screen capture might be black."
        )

    # 1. Capture Screen
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        screenshot = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    if DEVELOPER_MODE and DEV_SAVE_SCREENSHOTS:
        timestamp = str(int(time.time()))
        path = os.path.join(SCREENSHOTS_DIR, f"screen_{timestamp}.png")
        screenshot.save(path)

    # 2. Gemini Analysis
    logger.debug(f"Analyzing screen (Hint: {mode_hint})...")
    gemini_result = get_gemini_response(
        screenshot,
        enable_detailed_mode=ENABLE_DETAILED_MODE,
        question_type_hint=mode_hint,
    )

    if not gemini_result:
        logger.warning("Empty response from AI.")
        return False, last_processed_question

    q_type = gemini_result.get("type", "SAFE")
    question_text = gemini_result.get("question")
    answer_text = gemini_result.get("answer_text")

    # Idempotency Check (Skip if Auto Mode and same question)
    if (
        not bypass_idempotency
        and question_text
        and question_text == last_processed_question
    ):
        logger.info("Same question detected. Skipping.")
        return False, last_processed_question

    # For MULTI_MCQ, answers are in an array; for others, use answer_text
    answers_list = gemini_result.get("answers", [])
    
    if q_type == "SAFE":
        logger.info(f"No actionable question detected ({q_type}).")
        return False, question_text
    
    # Check if we have any actionable answers
    if q_type == "MULTI_MCQ":
        if not answers_list:
            logger.info("No answers found for MULTI_MCQ.")
            return False, question_text
        logger.info(f"QUESTION DETECTED ({q_type}). Found {len(answers_list)} correct answers.")
    else:
        if not answer_text:
            logger.info(f"No actionable question detected ({q_type}).")
            return False, question_text
        logger.info(f"QUESTION DETECTED ({q_type}). Target: '{answer_text[:50]}...'")
    action_taken = False

    # Force type if hint provides it (Override Gemini classification if needed, or trust Gemini with hint)
    # The prompt usually handles it, but we can verify.

    # --- MCQ LOGIC ---
    if q_type == "MCQ":
        logger.info("Processing MCQ...")
        coordinates = find_text_coordinates(screenshot, answer_text)

        if coordinates:
            x, y = coordinates
            final_x = x + monitor["left"]
            final_y = y + monitor["top"]
            
            # Simulate human reading/thinking before clicking
            simulate_reading_pause(0.3, 1.2)
            
            logger.info(f"Clicking at ({final_x}, {final_y})")
            click_at(final_x, final_y)
            move_away_from_options()  # Move mouse away after selection
            action_taken = True
        else:
            # Failsafe
            bbox = gemini_result.get("bbox")
            if bbox and len(bbox) == 4:
                ymin, xmin, ymax, xmax = bbox
                monitor_w, monitor_h = monitor["width"], monitor["height"]

                center_x = int(((xmin + xmax) / 2 / 1000) * monitor_w) + monitor["left"]
                center_y = int(((ymin + ymax) / 2 / 1000) * monitor_h) + monitor["top"]
                
                # Simulate human reading/thinking before clicking
                simulate_reading_pause(0.3, 1.2)

                logger.info(f"FAILSAFE Click: ({center_x}, {center_y})")
                click_at(center_x, center_y)
                move_away_from_options()  # Move mouse away after selection
                action_taken = True
            else:
                logger.error("Failsafe Failed: No valid bbox.")

    # --- MULTI_MCQ LOGIC (Multiple Correct Answers) ---
    elif q_type == "MULTI_MCQ":
        logger.info(f"Processing MULTI_MCQ with {len(answers_list)} answers...")
        monitor_w, monitor_h = monitor["width"], monitor["height"]
        
        clicked_count = 0
        for idx, answer_item in enumerate(answers_list):
            ans_text = answer_item.get("answer_text", "")
            ans_bbox = answer_item.get("bbox", [])
            
            logger.info(f"  [{idx + 1}/{len(answers_list)}] Target: '{ans_text[:40]}...'")
            
            # Try to find text coordinates first
            coordinates = find_text_coordinates(screenshot, ans_text)
            
            if coordinates:
                x, y = coordinates
                final_x = x + monitor["left"]
                final_y = y + monitor["top"]
                
                # Simulate human reading/thinking before clicking
                simulate_reading_pause(0.3, 1.0)
                
                logger.info(f"  Clicking at ({final_x}, {final_y})")
                click_at(final_x, final_y)
                clicked_count += 1
                
                # Brief pause between clicks (human-like)
                if idx < len(answers_list) - 1:
                    time.sleep(random.uniform(0.4, 0.8))
            elif ans_bbox and len(ans_bbox) == 4:
                # Failsafe: use bounding box
                ymin, xmin, ymax, xmax = ans_bbox
                center_x = int(((xmin + xmax) / 2 / 1000) * monitor_w) + monitor["left"]
                center_y = int(((ymin + ymax) / 2 / 1000) * monitor_h) + monitor["top"]
                
                # Simulate human reading/thinking before clicking
                simulate_reading_pause(0.3, 1.0)
                
                logger.info(f"  FAILSAFE Click: ({center_x}, {center_y})")
                click_at(center_x, center_y)
                clicked_count += 1
                
                # Brief pause between clicks (human-like)
                if idx < len(answers_list) - 1:
                    time.sleep(random.uniform(0.4, 0.8))
            else:
                logger.warning(f"  Could not locate answer: '{ans_text[:30]}...'")
        
        if clicked_count > 0:
            move_away_from_options()  # Move mouse away after all selections
            action_taken = True
            logger.info(f"MULTI_MCQ: Successfully clicked {clicked_count}/{len(answers_list)} answers.")
        else:
            logger.error("MULTI_MCQ: Failed to click any answers.")

    # --- DESCRIPTIVE LOGIC ---
    elif q_type == "DESCRIPTIVE" and ENABLE_DETAILED_MODE:
        if "bbox" in gemini_result and gemini_result["bbox"]:
            logger.info("Clicking text area to focus...")
            bbox = gemini_result["bbox"]
            if len(bbox) == 4:
                ymin, xmin, ymax, xmax = bbox
                monitor = mss.mss().monitors[
                    1
                ]  # We need to re-get monitor dims or cache them.
                # Actually 'monitor' var is local to Capture block. We need to handle this cleaner.
                # Re-invoking mss here is cheap enough or we should move monitor to outer scope.
                # Let's just grab valid monitor info again purely for dimension calculation.
                with mss.mss() as sct_temp:
                    monitor_temp = sct_temp.monitors[1]
                    monitor_w, monitor_h = monitor_temp["width"], monitor_temp["height"]
                    center_x = (
                        int(((xmin + xmax) / 2 / 1000) * monitor_w)
                        + monitor_temp["left"]
                    )
                    center_y = (
                        int(((ymin + ymax) / 2 / 1000) * monitor_h)
                        + monitor_temp["top"]
                    )
                    click_at(center_x, center_y)
                    time.sleep(0.5)

        type_text_human_like(
            answer_text, min_wpm=TYPING_WPM_MIN, max_wpm=TYPING_WPM_MAX
        )
        action_taken = True

    if action_taken and question_text:
        last_processed_question = question_text

    return action_taken, last_processed_question


def manual_trigger(mode_hint):
    """
    Blocking function called when hotkey is pressed.
    """
    logger.info(f"MANUAL TRIGGER DETECTED: {mode_hint}")
    logger.info(f"Waiting {HOTKEY_DELAY}s before capture...")
    time.sleep(HOTKEY_DELAY)

    action, _ = process_screen_cycle(mode_hint=mode_hint, bypass_idempotency=True)

    if action:
        logger.info("Manual Action Completed.")
    else:
        logger.warning("Manual Action Failed or No Question Found.")

    logger.info("Returning to silent background mode...")


def get_clipboard_content():
    """
    Get the current clipboard content.
    Returns the text content or None if clipboard is empty or not text.
    """
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                return data
            elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_TEXT):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_TEXT)
                return data.decode('utf-8', errors='ignore')
        finally:
            win32clipboard.CloseClipboard()
    except ImportError:
        # Fallback to pyperclip if win32clipboard not available
        try:
            import pyperclip
            return pyperclip.paste()
        except ImportError:
            logger.error("Neither win32clipboard nor pyperclip available. Install pywin32 or pyperclip.")
            return None
    except Exception as e:
        logger.error(f"Failed to read clipboard: {e}")
        return None
    return None


def clipboard_stream_trigger():
    """
    Triggered when clipboard stream hotkey is pressed.
    Reads the latest clipboard content and types it character by character.
    Uses the same controls as the existing typing engine:
    - Backspace: Pause/Resume
    - 9: Emergency Stop
    - Right Arrow: Speed Up
    """
    logger.info("CLIPBOARD STREAM TRIGGERED")
    logger.info(f"Waiting {HOTKEY_DELAY}s before reading clipboard...")
    time.sleep(HOTKEY_DELAY)
    
    # Get fresh clipboard content
    clipboard_text = get_clipboard_content()
    
    if not clipboard_text:
        logger.warning("Clipboard is empty or contains non-text content.")
        return
    
    clipboard_text = clipboard_text.strip()
    if not clipboard_text:
        logger.warning("Clipboard contains only whitespace.")
        return
    
    logger.info(f"Streaming clipboard content ({len(clipboard_text)} chars)...")
    logger.info("Controls: Backspace=Pause, 9=Stop, Right Arrow=Speed Up")
    
    # Use the existing human-like typing engine
    type_text_human_like(
        clipboard_text,
        min_wpm=TYPING_WPM_MIN,
        max_wpm=TYPING_WPM_MAX
    )
    
    logger.info("Clipboard stream complete.")
    logger.info("Returning to silent background mode...")


def main():
    if not DEVELOPER_MODE:
        pyautogui.FAILSAFE = False

    logger.info("🔮 Scry Started - Divine your answers.")
    
    # Register PID file cleanup
    atexit.register(remove_pid_file)
    create_pid_file()

    
    # Check for updates
    try:
        check_and_update()
    except Exception as e:
        logger.error(f"Update check failed: {e}")

    # ==========================================================================
    # LICENSE VALIDATION (if enabled)
    # ==========================================================================
    if REQUIRE_LICENSE:
        logger.info("🔐 Session license required. Validating...")
        if not validate_license():
            logger.error("❌ License validation failed. Exiting.")
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror(
                    "License Required",
                    "This software requires a valid license key to run.\n\n"
                    "Please contact the administrator for a license key."
                )
                root.destroy()
            except Exception:
                pass
            sys.exit(1)
        logger.info("✓ License validated successfully.")

    # Reset mouse fatigue counter for fresh session
    reset_fatigue()

    logger.info(f"Starting Mode: {'MANUAL (Hotkeys Only)' if is_manual_mode else 'AUTO (Loop)'}")
    logger.info(f"Detailed Mode: {ENABLE_DETAILED_MODE}")

    # Startup Wait
    logger.info(f"Waiting {INITIAL_WAIT} seconds before activating...")
    time.sleep(INITIAL_WAIT)

    # ==========================================================================
    # REGISTER ALL HOTKEYS (always active regardless of mode)
    # ==========================================================================
    # MCQ, Descriptive, Clipboard are always available
    triple_press_tracker.register_hotkey(HOTKEY_MCQ, lambda: manual_trigger("MCQ"))
    triple_press_tracker.register_hotkey(HOTKEY_DESCRIPTIVE, lambda: manual_trigger("DESCRIPTIVE"))
    triple_press_tracker.register_hotkey(HOTKEY_CLIPBOARD, clipboard_stream_trigger)
    
    # Multi-Select MCQ - only works in MANUAL mode (handled in the trigger)
    def multi_mcq_trigger():
        """Wrapper that only allows MULTI_MCQ in manual mode."""
        if is_manual_mode:
            manual_trigger("MULTI_MCQ")
        else:
            logger.warning("Multi-Select MCQ is only available in MANUAL mode.")
            logger.info(f"Press '{HOTKEY_TOGGLE_MODE}' 3x to switch to MANUAL mode first.")
    
    triple_press_tracker.register_hotkey(HOTKEY_MULTI_MCQ, multi_mcq_trigger)
    
    # Mode toggle hotkey
    triple_press_tracker.register_hotkey(HOTKEY_TOGGLE_MODE, toggle_mode)
    
    # Set up global key listener (always active)
    keyboard.on_press(triple_press_tracker.on_key_press)
    
    # Log initial mode info
    mode_name = "MANUAL MODE" if is_manual_mode else "AUTO MODE"
    logger.info(f"{mode_name} ACTIVE.")
    log_current_mode_info()

    # ==========================================================================
    # UNIFIED MAIN LOOP (supports dynamic mode switching)
    # ==========================================================================
    iteration_count = 0
    last_update_check = time.time()
    last_mode = is_manual_mode  # Track mode changes
    
    try:
        while True:
            # Check for mode change and log it
            if last_mode != is_manual_mode:
                last_mode = is_manual_mode
                # Mode was just switched, info already logged by toggle_mode()
            
            # Periodic Update Check (in both modes)
            if time.time() - last_update_check > UPDATE_CHECK_INTERVAL_SECONDS:
                logger.debug("Running periodic update check...")
                try:
                    check_and_update()  # Will exit/restart if update occurs
                except Exception as e:
                    logger.error(f"Periodic update check failed: {e}")
                last_update_check = time.time()

            if is_manual_mode:
                # MANUAL MODE: Just sleep and wait for hotkey triggers
                # The keyboard listener handles hotkeys in the background
                time.sleep(0.5)  # Short sleep to prevent CPU spinning
            else:
                # AUTO MODE: Poll screen and auto-detect questions
                iteration_count += 1
                logger.debug(f"--- Auto Iteration {iteration_count} ---")

                # In AUTO mode, only process MCQ and DESCRIPTIVE (not MULTI_MCQ)
                action_taken, _ = process_screen_cycle(
                    mode_hint=None, bypass_idempotency=False
                )

                if action_taken:
                    time.sleep(POST_ACTION_WAIT)
                else:
                    time.sleep(POLL_INTERVAL)

                if DEVELOPER_MODE and iteration_count >= DEV_MAX_ITERATIONS:
                    logger.info("Dev limit reached.")
                    break

    except KeyboardInterrupt:
        logger.info("Stopped by user.")
    except Exception as e:
        logger.critical(f"Error: {e}")
        logger.debug(traceback.format_exc())


if __name__ == "__main__":
    main()
