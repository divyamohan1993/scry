import argparse
import os
import sys
import threading
import time
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from unittest.mock import patch

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import main  # noqa: E402
from src.logger import get_logger  # noqa: E402

logger = get_logger("RealWorldSim")

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
            "Polymorphism allows objects of different classes to be treated as objects of a common superclass. "
            "It is a core concept of Object-Oriented Programming (OOP)."
        ),
        "marks": 10,
        "bbox": [400, 200, 600, 800],  # Approximate center for textarea
    },
}


class TestServer(threading.Thread):
    def __init__(self):
        super().__init__()
        # Port 0 lets OS pick a free port
        self.server = HTTPServer(("localhost", 0), SimpleHTTPRequestHandler)
        self.server_port = self.server.server_address[1]
        self.daemon = True  # Kill when main thread exits

    def run(self):
        # Serve from tests/pages
        os.chdir(os.path.join(os.path.dirname(__file__), "pages"))
        print(f"Starting test server at http://localhost:{self.server_port}...")
        self.server.serve_forever()


def run_simulation_step(mode, port, use_real_ai=False):
    """
    mode: 'MCQ' or 'DESCRIPTIVE'
    """
    print(f"\n=== STARTING LIVE SIMULATION: {mode} (Real AI: {use_real_ai}) ===")

    # 1. Open Browser
    url = f"http://localhost:{port}/{'mcq_test.html' if mode == 'MCQ' else 'descriptive_test.html'}"
    print(f"Opening {url}...")
    webbrowser.open(url)

    # Give browser time to render and user to focus
    print("Waiting 5s for browser to load and maximize...")
    time.sleep(5)

    # 2. Run Main Cycle
    if use_real_ai:
        print(" Using REAL Gemini API (Cost involved)...")
        # Ensure detailed mode is ON if descriptive
        with patch("src.main.ENABLE_DETAILED_MODE", True):
            action_taken, question = main.process_screen_cycle(
                mode_hint=mode, bypass_idempotency=True
            )
    else:
        print(" Using MOCKED Gemini response (Zero cost, deterministic)...")
        mock_response = MOCK_RESPONSES[mode]
        # Patch get_gemini_response
        with patch("src.main.get_gemini_response", return_value=mock_response):
            # Patch ENABLE_DETAILED_MODE to True for this test
            with patch("src.main.ENABLE_DETAILED_MODE", True):
                action_taken, question = main.process_screen_cycle(
                    mode_hint=mode, bypass_idempotency=True
                )

    if action_taken:
        print(f"SUCCESS: Action was taken for {mode}.")
        if question:
            print(f"Question processed: {question}")
    else:
        print(f"FAILURE: No action taken for {mode}.")


def main_cli():
    parser = argparse.ArgumentParser(description="Run Real World Simulation")
    parser.add_argument(
        "--real-ai", action="store_true", help="Use real Gemini API instead of mocks"
    )
    args = parser.parse_args()

    # Start Server
    server_thread = TestServer()
    server_thread.start()
    time.sleep(2)  # Wait for server

    print("==================================================================")
    print(" LIVE SIMULATION - HANDS OFF THE MOUSE/KEYBOARD")
    print("==================================================================")

    try:
        # Run MCQ Test
        run_simulation_step("MCQ", server_thread.server_port, use_real_ai=args.real_ai)

        # Wait between tests
        print("Waiting 5s before next test...")
        time.sleep(5)

        # Run Descriptive Test
        run_simulation_step(
            "DESCRIPTIVE", server_thread.server_port, use_real_ai=args.real_ai
        )

    except KeyboardInterrupt:
        print("Simulation stopped.")
    except Exception as e:
        print(f"Simulation Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("Simulation complete.")


if __name__ == "__main__":
    # Ensure config allows us to run
    # config.DEVELOPER_MODE = True
    main_cli()
