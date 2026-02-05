import ctypes
import logging
import random
import time
import os


import keyboard

from src.runtime_config import get_config

# Setup logger
logger = logging.getLogger("TypingEngine")

# Windows API for Input
user32 = ctypes.windll.user32
INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002
VK_RETURN = 0x0D
VK_BACK = 0x08


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT_I(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", INPUT_I)]


def _send_vk(vk_code):
    """Sends a virtual key code using keyboard library."""
    try:
        if vk_code == VK_RETURN:
            keyboard.send("enter")
        elif vk_code == VK_BACK:
            keyboard.send("backspace")
        else:
            pass
    except Exception as e:
        logger.error(f"Keyboard lib error: {e}")


def _send_char(char):
    """Sends a unicode character using keyboard library."""
    try:
        keyboard.write(char)
    except Exception as e:
        logger.error(f"Keyboard lib write error: {e}")


# =============================================================================
# DATA MODELS
# =============================================================================

# QWERTY Map for typo simulation
QWERTY_MAP = {
    "q": ["w", "a", "s"],
    "w": ["q", "e", "a", "s", "d"],
    "e": ["w", "r", "s", "d", "f"],
    "r": ["e", "t", "d", "f", "g"],
    "t": ["r", "y", "f", "g", "h"],
    "y": ["t", "u", "g", "h", "j"],
    "u": ["y", "i", "h", "j", "k"],
    "i": ["u", "o", "j", "k", "l"],
    "o": ["i", "p", "k", "l"],
    "p": ["o", "l"],
    "a": ["q", "w", "s", "z"],
    "s": ["w", "e", "a", "d", "z", "x"],
    "d": ["e", "r", "s", "f", "x", "c"],
    "f": ["r", "t", "d", "g", "c", "v"],
    "g": ["t", "y", "f", "h", "v", "b"],
    "h": ["y", "u", "g", "j", "b", "n"],
    "j": ["u", "i", "h", "k", "n", "m"],
    "k": ["i", "o", "j", "l", "m"],
    "l": ["o", "p", "k"],
    "z": ["a", "s", "x"],
    "x": ["s", "d", "z", "c"],
    "c": ["d", "f", "x", "v"],
    "v": ["f", "g", "c", "b"],
    "b": ["g", "h", "v", "n"],
    "n": ["h", "j", "b", "m"],
    "m": ["j", "k", "n"],
}

# Key Frequency "Heatmap" - Delay Multipliers
# Common keys (e, t, a, o) are typed faster (factor < 1.0)
# Rare/Awkward keys (z, x, q) are typed slower (factor > 1.0)
KEY_DELAY_FACTOR = {
    "e": 0.85,
    "t": 0.88,
    "a": 0.88,
    "o": 0.9,
    "i": 0.9,
    "n": 0.9,
    "s": 0.95,
    "h": 0.95,
    "r": 0.95,
    "d": 0.98,
    "l": 0.98,
    "u": 1.0,
    "c": 1.0,
    "m": 1.0,
    "f": 1.05,
    "w": 1.05,
    "y": 1.05,
    "p": 1.1,
    "v": 1.1,
    "b": 1.1,
    "g": 1.1,
    "k": 1.15,
    "j": 1.2,
    "q": 1.25,
    "x": 1.3,
    "z": 1.35,
}

# Muscle Memory Words (Typed significantly faster)
MUSCLE_MEMORY_WORDS = {
    "the",
    "and",
    "that",
    "with",
    "have",
    "this",
    "will",
    "your",
    "from",
    "they",
    "know",
    "want",
    "been",
    "good",
    "much",
    "some",
    "time",
    "very",
    "when",
    "come",
    "here",
    "just",
    "like",
    "long",
    "make",
    "many",
    "more",
    "only",
    "over",
    "such",
    "take",
    "than",
    "them",
    "then",
    "were",
    "because",
    "should",
    "would",
    "what",
    "which",
    "there",
    "their",
    "about",
}


class HumanTypist:
    """
    A highly advanced human typing simulator.
    """

    def __init__(self, min_wpm=30, max_wpm=100, error_rate=0.05):
        """
        :param min_wpm: Minimum Words Per Minute
        :param max_wpm: Maximum Words Per Minute
        :param error_rate: Probability of making a mistake per WORD (approx 1 in 20)
        """
        self.base_min_wpm = min_wpm
        self.base_max_wpm = max_wpm

        # Urgent mode override - maximum speed, no delays
        # Read dynamically on each init to support runtime changes
        self.urgent_mode = get_config("URGENT_MODE", False)
        if self.urgent_mode:
            logger.info("HumanTypist: 'URGENT_MODE' active! Typing at MAXIMUM SPEED (no WPM cap).")
            self.error_rate = 0.0  # No errors in urgent mode
        else:
            self.error_rate = error_rate

        self.paused = False
        self.stopped = False
        self.speed_multiplier = 1.0
        self.hooks = []

    def _emergency_stop(self, e):
        """Stops typing immediately."""
        self.stopped = True
        logger.warning("HumanTypist: Emergency STOP triggered by user (9).")

    def _increase_speed_multiplier(self, e):
        """Speeds up typing by 10% per press."""
        self.speed_multiplier *= 1.1
        logger.info(f"Speed UP! Multiplier: {self.speed_multiplier:.2f}x")

    def _toggle_pause(self, e):
        self.paused = not self.paused
        state = "PAUSED" if self.paused else "RESUMED"
        logger.info(f"Typing {state} by user (Backspace).")

    def _wait_if_paused(self):
        while self.paused and not self.stopped:
            time.sleep(0.1)

    def _get_base_delay(self, wpm):
        """
        Calculates the base inter-key delay (seconds) for a target WPM.
        Standard Formula: WPM = (CPM / 5). CPM = WPM * 5.
        Delay = 60 / CPM = 60 / (WPM * 5) = 12 / WPM.
        """
        # Apply the user speed multiplier
        effective_wpm = wpm * self.speed_multiplier
        if effective_wpm < 10:
            effective_wpm = 10  # Floor to prevent infinite delay

        return 12.0 / effective_wpm

    def _calculate_word_complexity(self, word):
        """AI-like heuristic to determine word complexity."""
        # Simple heuristic: Length + Rare characters
        score = len(word)
        for char in word.lower():
            if char in "qzxjk":
                score += 1.5
            elif char in "vpbg":
                score += 0.5
        return score

    def type_text(self, text: str):
        """Types the given text with simulated human strategies."""
        self.stopped = False
        self.paused = False
        
        # Always reset speed multiplier to default at the start of each session
        # This ensures that previous acceleration (via right arrow) doesn't persist
        self.speed_multiplier = 1.0
        logger.info(f"HumanTypist: Starting new session (WPM: {self.base_min_wpm}-{self.base_max_wpm}, Speed: 1.0x)")

        if not text:
            return

        # --- INSTANCE LOCKING ---
        lock_file = os.path.join(os.path.dirname(__file__), "typing.lock")
        if os.path.exists(lock_file):
            # Check age of lock file to avoid deadlocks from crashes
            try:
                if time.time() - os.path.getmtime(lock_file) > 120:  # 2 mins old
                    logger.warning("Stale lock file found. Overwriting.")
                else:
                    logger.warning("Another typing instance is running. Aborting this request.")
                    return
            except Exception:
                pass
        
        # Create Lock
        try:
             with open(lock_file, "w") as f:
                 f.write(str(time.time()))
        except Exception as e:
            logger.error(f"Could not create lock file: {e}")
            return

        # Monitor Screen Thread
        # We need to detect if screen changes. Since we can't easily multithread MSS inside this synchronous function without care,
        # we will use a simple check in the typing loop, utilizing a helper.
        # But grabbing screen takes time. We should only check occasionally or check ACTIVE WINDOW.
        # Checking Active Window is fast (user32).
        
        initial_window = ctypes.windll.user32.GetForegroundWindow()

        logger.info(
            f"HumanTypist: Typing {len(text)} chars (Base WPM: {self.base_min_wpm}-{self.base_max_wpm})...."
        )

        # Hook Keys
        try:
            self.hooks.append(
                keyboard.on_press_key("backspace", self._toggle_pause, suppress=True)
            )
            self.hooks.append(
                keyboard.on_press_key("9", self._emergency_stop, suppress=True)
            )
            self.hooks.append(
                keyboard.on_press_key(
                    "right", self._increase_speed_multiplier, suppress=True
                )
            )
        except Exception as e:
            logger.error(f"Failed to hook keys: {e}")

        try:
            # Initial "Thinking" / Analyzing (skip in urgent mode)
            if not self.urgent_mode:
                time.sleep(random.uniform(0.1, 0.5))

            # Split into paragraphs to simulate paragraph-level thinking
            paragraphs = text.split("\n")

            for p_idx, paragraph in enumerate(paragraphs):
                if self.stopped:
                    break

                # Paragraph break thinking (if not first)
                if p_idx > 0:
                    _send_vk(VK_RETURN)
                    # Thinking after newline (skip in urgent mode)
                    if not self.urgent_mode:
                        time.sleep(random.uniform(0.5, 1.2))

                words = paragraph.split(" ")
                i_word = 0

                while i_word < len(words):
                    if self.stopped:
                        break
                    
                    # --- SCREEN STABILITY CHECK ---
                    current_window = ctypes.windll.user32.GetForegroundWindow()
                    if current_window != initial_window:
                        if not self.paused:
                            logger.warning("Focus lost! Pausing typing. Press Backspace to resume when ready.")
                            self.paused = True
                    
                    self._wait_if_paused()

                    word = words[i_word]

                    # --- DYNAMIC WPM CALCULATION ---
                    # 1. Base random range
                    target_wpm = random.uniform(self.base_min_wpm, self.base_max_wpm)

                    # 2. Adjust based on word familiarity/length
                    if word.lower() in MUSCLE_MEMORY_WORDS:
                        target_wpm *= 1.4  # Muscle memory speed boost
                    else:
                        complexity = self._calculate_word_complexity(word)
                        if complexity > 8:
                            target_wpm *= 0.7  # Complex/Long word slowdown
                        elif complexity < 4:
                            target_wpm *= 1.1  # Short simple word speedup

                    # --- AI ERROR / RETHINK SIMULATION (skip in urgent mode) ---
                    # 3. Simulate "Rethinking" (Delete previous word)
                    # Chance: ~1 in 40 words? (Prompt said "sometimes entire word... 1 mistake in 20 words")
                    # Let's say "Rethink" is rarer than simple typo.
                    if not self.urgent_mode and i_word > 0 and random.random() < 0.025:  # 2.5% chance
                        self._perform_rewrite(words[i_word - 1])
                        # After rewrite, we are back at current word.

                    # 4. Type the word
                    # Check for simple typo (1 in 20 words = 5%)
                    make_mistake = random.random() < self.error_rate

                    self._type_word(word, target_wpm, make_mistake)

                    # 5. Space / Punctuation Logic
                    if i_word < len(words) - 1:
                        _send_char(" ")
                        # Space timing (skip delay in urgent mode)
                        if not self.urgent_mode:
                            time.sleep(self._get_base_delay(target_wpm))

                    # 6. Strategize: Post-word pauses (skip in urgent mode)
                    if not self.urgent_mode:
                        if word.endswith((".", "?", "!")):
                            # End of sentence thinking
                            time.sleep(random.uniform(0.3, 0.7))
                        elif word.endswith((",", ";", ":")):
                            # Clause pause
                            time.sleep(random.uniform(0.15, 0.3))

                    i_word += 1

            logger.info("HumanTypist: Complete.")

        finally:
            # Cleanup Lock
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except:
                    pass
            # Unhook
            for h in self.hooks:
                try:
                    keyboard.unhook(h)
                except Exception as e:
                    logger.error(f"Failed to unhook: {e}")
            self.hooks = []

    def _type_word(self, word, wpm, make_mistake=False):
        """Types a single word, handling char-by-char delays and heatmap."""

        # Decide WHERE the mistake happens if allowed
        mistake_index = -1
        if make_mistake and len(word) > 1:
            mistake_index = random.randint(0, len(word) - 1)

        i_char = 0
        while i_char < len(word):
            if self.stopped:
                return
            self._wait_if_paused()

            char = word[i_char]

            # In urgent mode, skip all delay calculations
            if self.urgent_mode:
                delay = 0
            else:
                # Base Delay
                delay = self._get_base_delay(wpm)

                # --- KEY FREQUENCY HEATMAP APPLICATION ---
                lower_char = char.lower()
                if lower_char in KEY_DELAY_FACTOR:
                    delay *= KEY_DELAY_FACTOR[lower_char]

                # --- JITTER/VARIANCE ---
                # Fingers aren't robots; add noise (Gaussian)
                delay = random.gauss(delay, delay * 0.2)
                delay = max(0.005, delay)  # Minimum physical limit

            # Execute Mistake? (skip in urgent mode)
            if not self.urgent_mode and i_char == mistake_index:
                self._perform_typo(char)
                # After fixing typo, maybe slight delay getting back on track
                time.sleep(random.uniform(0.1, 0.2))
                # _perform_typo handles the wrong char + backspace,
                # effectively leaving us ready to type the correct char.
                # So we just continue to type the correct char now.

            # Type the (correct) character
            # Shift key simulation for uppercase (skip delay in urgent mode)
            if not self.urgent_mode and char.isupper():
                delay += 0.08  # Shift key press time

            _send_char(char)
            if delay > 0:
                time.sleep(delay)

            i_char += 1

    def _perform_typo(self, target_char):
        """Simulates hitting a wrong key, realizing, and backspacing."""
        lower_char = target_char.lower()

        # Determine likely wrong key (neighbor)
        if lower_char in QWERTY_MAP:
            wrong_char = random.choice(QWERTY_MAP[lower_char])
            if target_char.isupper():
                wrong_char = wrong_char.upper()
        else:
            wrong_char = chr(ord(target_char) + 1)  # Fallback

        # Type wrong char
        _send_char(wrong_char)

        # Reaction time (Oh shoot!) - "Thinking" delay
        time.sleep(random.uniform(0.15, 0.4))

        # Backspace
        _send_vk(VK_BACK)

        # Recovery time
        time.sleep(random.uniform(0.05, 0.15))

    def _perform_rewrite(self, previous_word):
        """
        Simulates deleting the entire previous word to rewrite it.
        analyzing -> waiting -> deleting -> retyping
        """
        if not previous_word:
            return

        logger.info(f"HumanTypist: Analyzing and rewriting '{previous_word}'...")

        # 1. Analyze / Think pause
        time.sleep(random.uniform(0.4, 0.8))

        # 2. Delete word + space
        count = len(previous_word) + 1
        for _ in range(count):
            _send_vk(VK_BACK)
            # Backspace speed is usually fast and rhythmic
            time.sleep(random.uniform(0.08, 0.12))

        # 3. Think again before retyping
        time.sleep(random.uniform(0.2, 0.5))

        # 4. Retype (Recursively calls _type_word, assume no mistakes this time to avoid infinite loop of frustration)
        # We assume the user retypes the SAME word (since we don't have an alternative text source here)
        # But this visualizes the behavior requested.
        self._type_word(previous_word, self.base_min_wpm * 1.1, make_mistake=False)
        _send_char(" ")
        time.sleep(0.1)
