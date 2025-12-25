import os
import sys
import threading
import time
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from unittest.mock import patch

from src import config, main

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import project modules

# Configure valid answers for the mock
MOCK_RESPONSES = {
    "MCQ": {
        "type": "MCQ",
        "question": "What is the capital city of France?",
        "answer_text": "Paris",  # Should match text in mcq_test.html
        "bbox": [500, 500, 600, 600],  # Dummy fallback, we expect OCR to find "Paris"
    },
    "DESCRIPTIVE": {
        "type": "DESCRIPTIVE",
        "question": "Explain the concept of Polymorphism...",
        "answer_text": (
            "Polymorphism allows objects of different classes to be treated as objects of a common superclass."
        ),
        "marks": 10,
    },
}


class TestServer(threading.Thread):
    def __init__(self):
        super().__init__()
        self.server = HTTPServer(("localhost", 8080), SimpleHTTPRequestHandler)
        self.daemon = True  # Kill when main thread exits

    def run(self):
        # Serve from tests/pages
        os.chdir(os.path.join(os.path.dirname(__file__), "pages"))
        print("Starting test server at http://localhost:8080...")
        self.server.serve_forever()


def run_simulation(mode):
    """
    mode: 'MCQ' or 'DESCRIPTIVE'
    """
    print(f"\n=== STARTING LIVE SIMULATION: {mode} ===")

    # 1. Open Browser
    url = f"http://localhost:8080/{'mcq_test.html' if mode == 'MCQ' else 'descriptive_test.html'}"
    print(f"Opening {url}...")
    webbrowser.open(url)

    # Give browser time to render and user to focus
    time.sleep(3)

    # 2. Mock Gemini (We only want to test the SCREEN Capture -> OCR -> ACTION pipeline)
    # The actual 'intelligence' is mocked to be deterministic.
    mock_response = MOCK_RESPONSES[mode]

    # 2. Mock Gemini (Deterministic) or Use Real AI
    # To test strictly, we mock. To test deployment, we can use real.
    USE_REAL_AI = False

    if USE_REAL_AI:
        print("Using REAL Gemini API...")
        action_taken, question = main.process_screen_cycle(
            mode_hint=mode, bypass_idempotency=True
        )
    else:
        # Correctly patch where it is IMPORTED in src.main
        with patch("src.main.get_gemini_response", return_value=mock_response):
            print("Mocked Gemini ready. Running detection cycle...")
            action_taken, question = main.process_screen_cycle(
                mode_hint=mode, bypass_idempotency=True
            )

        if action_taken:
            print(f"SUCCESS: Action was taken for {mode}.")
            print(f"Detected Question: {question}")
        else:
            print(f"FAILURE: No action taken for {mode}.")


def main_cli():
    # Start Server
    server_thread = TestServer()
    server_thread.start()
    time.sleep(1)  # Wait for server

    try:
        # Run MCQ Test
        run_simulation("MCQ")

        # Wait between tests
        time.sleep(3)

        # Run Descriptive Test
        run_simulation("DESCRIPTIVE")

    except KeyboardInterrupt:
        print("Simulation stopped.")
    finally:
        print("Simulation validation complete.")
        # Server daemon thread will die with main


if __name__ == "__main__":
    # Ensure config allows us to run
    config.DEVELOPER_MODE = True
    main_cli()
