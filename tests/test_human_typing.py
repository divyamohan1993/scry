import logging
import os
import sys
import time

# Add project root to path BEFORE importing src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.desktop_manager import type_text_human_like

# Setup logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main():
    print("==================================================")
    print("HUMAN TYPING TEST SIMULATION")
    print("==================================================")
    # Automatically running without delay for CI/Test Batch
    print("Running in autonomous mode (no delay).")
    
    # Optional: We could simulate Notepad opening here or just type into void if just testing execution
    # For now, we assume the environment is safe to type into since run_tests.bat warns users.
    time.sleep(1)

    sample_text = (
        "The quick brown fox jumps over the lazy dog. "
        "This is a test of the automatic typing system? "
        "I hope it looks very human-like! "
        "Sometimes I make mistakes, but I fix them."
    )

    start_time = time.time()
    type_text_human_like(sample_text, min_wpm=30, max_wpm=70, error_rate=0.04)
    end_time = time.time()

    duration = end_time - start_time
    wpm = (len(sample_text) / 5) / (duration / 60)

    print("\n==================================================")
    print(f"Total Time: {duration:.2f} seconds")
    print(f"Estimated WPM: {wpm:.2f}")
    print("Done.")


if __name__ == "__main__":
    main()
