
import os
import sys
import time
import threading
import webbrowser
import argparse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from unittest.mock import patch
import random

# Ensure we are using the venv
# In a real run, we expect the user/IDE to use the venv, but we can check sys.executable
# to see if it looks right, or just proceed. The USER requested "single endpoint", so this script 
# should be runnable directly.

# Add Source Path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import main
from src.gemini import client
from src.logger import get_logger

logger = get_logger("AutoSim")

GENERATED_PAGES_DIR = os.path.join(os.path.dirname(__file__), "pages")
os.makedirs(GENERATED_PAGES_DIR, exist_ok=True)

class TestServer(threading.Thread):
    def __init__(self):
        super().__init__()
        self.server = HTTPServer(("localhost", 0), SimpleHTTPRequestHandler)
        self.server_port = self.server.server_address[1]
        self.daemon = True

    def run(self):
        os.chdir(GENERATED_PAGES_DIR)
        logger.info("Serving at port {self.server_port}")
        self.server.serve_forever()

def generate_test_case_with_gemini(mode="MCQ"):
    """
    Asks Gemini to generate a valid HTML file with an MCQ or Descriptive question.
    Returns: (html_content, expected_answer_text)
    """
    logger.info(f"Asking Gemini to generate a unique {mode} test case...")
    
    if mode == "MCQ":
        prompt_specifics = (
            "It must contain exactly one Multiple Choice Question (MCQ) visible on screen. "
            "Include 4 options with radio buttons. "
            "Also provide the correct answer text exactly as it appears in the option. "
        )
    else: # DESCRIPTIVE
        prompt_specifics = (
            "It must contain exactly one 'Descriptive' question asking for a short definition. "
            "It MUST contain a visible <textarea> or <input type='text'> field for the answer. "
            "Also provide a sample correct short answer (1 sentence). "
        )

    prompt = (
        "Generate a simple, clean HTML file content for a mock Exam interface. "
        f"{prompt_specifics}"
        "Style it professionally (CSS). "
        "The question should be obscure but having a definitive factual answer. "
        "Output JSON format: {\"html\": \"...\", \"correct_answer\": \"...\"}"
        "Do not use markdown formatting, just raw JSON."
    )
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        text = response.text.replace("```json", "").replace("```", "").strip()
        import json
        data = json.loads(text)
        return data["html"], data["correct_answer"]
    except Exception as e:
        logger.error(f"Failed to generate test case: {e}")
        # Fallback
        return (
            "<html><body><h1>Error generating test</h1></body></html>", 
            "Error"
        )

def run_simulation_step(mode, html_content, expected_answer):
    # 1. Setup Page
    filename = f"auto_generated_test_{mode}.html"
    filepath = os.path.join(GENERATED_PAGES_DIR, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    logger.info(f"Generated test page: {filepath}")
    logger.info(f"EXPECTED ANSWER: {expected_answer}")

    # 2. Start Server (if not running, but assumes ThreadedServer usage pattern, 
    # we need a fresh server or reuse existing? 
    # Best to start one global server or just use one-off ports. 
    # The simplest way here without complex lifecycle management is to just start a new thread each time
    # provided we don't block. But we need to know the port. 
    # Let's start the server *once* if possible, or just new one each time.)
    
    server = TestServer()
    server.start()
    time.sleep(1) # Warm up

    # 3. Open Browser
    url = f"http://localhost:{server.server_port}/{filename}"
    logger.info(f"Opening {url}...")
    webbrowser.open(url)
    
    # Wait for browser to render
    time.sleep(5) 

    # 4. Run Screen Reader Logic
    real_get_gemini = main.get_gemini_response
    captured_response = {}

    def spy_get_gemini(*args, **kwargs):
        res = real_get_gemini(*args, **kwargs)
        captured_response['result'] = res
        return res

    
    # Run the cycle with REAL system interactions
    # We spy on get_gemini_response to verify the logic, but we let it call the real API
    # We do NOT mock click_at or switch_to_input_desktop anymore
    
    with patch('src.main.get_gemini_response', side_effect=spy_get_gemini):
        # Ensure Detailed Mode is active for Descriptive tests so typing happens
        if mode == "DESCRIPTIVE":
             with patch("src.main.ENABLE_DETAILED_MODE", True):
                 main.process_screen_cycle(mode_hint=mode, bypass_idempotency=True)
        else:
             main.process_screen_cycle(mode_hint=mode, bypass_idempotency=True)
            
        # 5. Analysis
        gemini_res = captured_response.get('result')
        if not gemini_res:
            logger.error("TEST FAILED: No response from Gemini.")
            return

        detected_answer = gemini_res.get('answer_text')
        detected_question = gemini_res.get('question')
        
        logger.info(f"AI Detected Question: {detected_question}")
        logger.info(f"AI Detected Answer: {detected_answer}")
        
        if not detected_answer:
             logger.error("[FAIL] TEST FAILED: No answer detected.")
             return

        # Loose comparison
        if expected_answer.lower() in detected_answer.lower() or detected_answer.lower() in expected_answer.lower():
            logger.info("[PASS] TEST PASSED: Detected answer intention matches expected.")
        else:
            logger.error(f"[FAIL] TEST FAILED: Discrepancy found! Expected '{expected_answer}' but got '{detected_answer}'")


def run_full_suite():
    # 1. Test MCQ (Clicking)
    logger.info("\n=== RUNNING MCQ SIMULATION (Testing Mouse Clicks) ===")
    html_mcq, ans_mcq = generate_test_case_with_gemini(mode="MCQ")
    run_simulation_step("MCQ", html_mcq, ans_mcq)

    # Short break between tests
    time.sleep(5)

    # 2. Test Descriptive (Typing)
    logger.info("\n=== RUNNING DESCRIPTIVE SIMULATION (Testing Human Typing) ===")
    html_desc, ans_desc = generate_test_case_with_gemini(mode="DESCRIPTIVE")
    run_simulation_step("DESCRIPTIVE", html_desc, ans_desc)

if __name__ == "__main__":
    try:
        run_full_suite()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
