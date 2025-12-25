import json

from google import genai

from .config import GEMINI_API_KEY
from .logger import get_logger

logger = get_logger("GeminiClient")
# Configure Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)


def get_gemini_response(
    image, prompt_text="", enable_detailed_mode=False, question_type_hint=None
):
    """
    Sends image to Gemini and gets a structured JSON response.
    Returns keys:
      - 'type': 'MCQ' or 'DESCRIPTIVE'
      - 'answer_text': The answer (or null)
      - 'bbox': [ymin, xmin, ymax, xmax] (0-1000) (For MCQ option to click)
      - 'marks': (int) for descriptive questions
    """
    hint_instruction = ""
    if question_type_hint == "MCQ":
        hint_instruction = (
            "IMPORTANT: The user has manually flagged this as an MCQ. "
            "Focus on identifying options (A, B, C, D) and the correct choice."
        )
    elif question_type_hint == "DESCRIPTIVE":
        hint_instruction = (
            "IMPORTANT: The user has manually flagged this as a DESCRIPTIVE question. "
            "Ignore radio buttons and generate a text answer based on the marks."
        )

    # Enhanced prompt with Conditional Logic
    final_prompt = (
        "Analyze the provided screen image. \n"
        f"{hint_instruction}\n"
        "1. CLASSIFY: Determine the Question Type.\n"
        "   - 'MCQ': If there are radio buttons, checkboxes, or clear options (A, B, C, D).\n"
        "   - 'DESCRIPTIVE': If there is a text box or a question asking for an explanation/definition.\n"
        "   - 'SAFE': Login screens, desktops, errors, or no distinct question.\n"
        "\n"
        "2. SOLVE:\n"
        "   - IF MCQ: Identify the Correct Answer Option.\n"
        "   - IF DESCRIPTIVE: \n"
        f"        - ENABLED: {enable_detailed_mode}\n"
        "        - If ENABLED is true: Read the 'Marks' (e.g. 2 marks, 5 marks, 10 marks). Default to 5 if unknown.\n"
        "        - Generate a high-quality answer. **Length Rule**:\n"
        "             - 2 Marks = 1-2 sentences.\n"
        "             - 5 Marks = 1 short paragraph (3-4 sentences).\n"
        "             - 10 Marks = 2 paragraphs.\n"
        "             - 20 Marks = Detailed explanation.\n"
        "        - If ENABLED is false: Return null for answer_text.\n"
        "\n"
        "3. OUTPUT: Return PURE VALID JSON:\n"
        "{\n"
        '  "type": "MCQ" | "DESCRIPTIVE" | "SAFE",\n'
        '  "question": "Question text",\n'
        '  "answer_text": "Correct answer text (for MCQ or Descriptive)",\n'
        '  "marks": int (or null),\n'
        '  "bbox": [ymin, xmin, ymax, xmax] (For MCQ option OR Descriptive input field. 0-1000)\n'
        "}\n"
        "Do not use markdown code blocks. Just valid JSON."
    )

    try:
        logger.debug("Sending request to Gemini (Model: gemini-3-flash-preview)...")

        response = client.models.generate_content(
            model="gemini-3-flash-preview", contents=[final_prompt, image]
        )

        raw_text = response.text.strip()
        logger.debug(f"Gemini Raw Response: {raw_text}")

        # Clean up JSON if wrapped in markdown
        cleaned_text = raw_text
        if "```json" in cleaned_text:
            cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned_text:
            cleaned_text = cleaned_text.split("```")[1].split("```")[0].strip()

        # Parse JSON
        result = json.loads(cleaned_text)
        logger.info(
            f"Gemini Analysis: Question='{result.get('question')}' | Answer='{result.get('answer_text')}'"
        )
        return result

    except Exception as e:
        logger.error(f"Error communicating with Gemini: {e}")
        # Fallback (Compact)
        try:
            logger.info("Retrying with gemini-2.5-flash (JSON Mode)...")
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=[final_prompt, image]
            )
            raw_text = response.text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            return json.loads(raw_text)
        except Exception as e2:
            logger.error(f"Fallback failed: {e2}")
            return None
