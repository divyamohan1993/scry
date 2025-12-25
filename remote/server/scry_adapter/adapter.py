"""
Scry Remote - Scry Adapter

Adapter that interfaces with the existing Scry software without modifying it.
Uses the Gemini API directly (same as Scry) to analyze screenshots and
generate control commands.

This module exists as a clean separation layer - it can either:
1. Call Scry functions directly (if in same process)
2. Call Gemini API directly (standalone mode)
3. Communicate with Scry via subprocess (isolation mode)
"""

import asyncio
import json
from typing import Optional, Dict, Any
from pathlib import Path
import sys

from PIL import Image
from loguru import logger
from google import genai

from ..config import GEMINI_API_KEY, ENABLE_DETAILED_MODE, SCRY_PATH


class ScryAdapter:
    """
    Adapter for Scry AI analysis.
    
    This adapter provides the same functionality as Scry's main loop
    but designed for remote operation:
    - Takes a PIL Image instead of capturing screen
    - Returns control commands instead of executing them locally
    
    Modes:
    - 'api': Direct Gemini API calls (default)
    - 'import': Import Scry modules directly
    - 'subprocess': Run Scry as subprocess (maximum isolation)
    """
    
    def __init__(self, mode: str = "api"):
        self.mode = mode
        self._client = None
        
        if mode == "api":
            self._client = genai.Client(api_key=GEMINI_API_KEY)
            logger.info("ScryAdapter initialized in API mode")
        elif mode == "import":
            self._setup_import_mode()
        elif mode == "subprocess":
            self._setup_subprocess_mode()
        else:
            raise ValueError(f"Unknown mode: {mode}")
    
    def _setup_import_mode(self):
        """Setup to import Scry modules directly."""
        scry_path = Path(SCRY_PATH)
        if scry_path.exists() and str(scry_path) not in sys.path:
            sys.path.insert(0, str(scry_path))
        
        try:
            from src.gemini import get_gemini_response
            from src.utils.screen import find_text_coordinates
            self._get_gemini_response = get_gemini_response
            self._find_text_coordinates = find_text_coordinates
            logger.info("ScryAdapter initialized in import mode")
        except ImportError as e:
            logger.error(f"Failed to import Scry modules: {e}")
            raise
    
    def _setup_subprocess_mode(self):
        """Setup for subprocess communication."""
        # TODO: Implement subprocess communication
        logger.info("ScryAdapter initialized in subprocess mode")
    
    async def analyze_image(
        self,
        image: Image.Image,
        question_type_hint: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze an image and return control commands.
        
        Args:
            image: PIL Image to analyze
            question_type_hint: 'MCQ' or 'DESCRIPTIVE' hint
        
        Returns:
            Dict with:
            - 'type': 'MCQ', 'DESCRIPTIVE', or 'SAFE'
            - 'action': 'click', 'type', or None
            - 'x', 'y': Coordinates for click (normalized 0-1)
            - 'text': Text to type (for DESCRIPTIVE)
            - 'answer_text': The answer found
        """
        if self.mode == "api":
            return await self._analyze_with_api(image, question_type_hint)
        elif self.mode == "import":
            return await self._analyze_with_import(image, question_type_hint)
        elif self.mode == "subprocess":
            return await self._analyze_with_subprocess(image, question_type_hint)
        
        return None
    
    async def _analyze_with_api(
        self,
        image: Image.Image,
        question_type_hint: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Analyze image using direct Gemini API calls."""
        
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
        
        # Build prompt - same as Scry's gemini.py
        prompt = (
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
            f"        - ENABLED: {ENABLE_DETAILED_MODE}\n"
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
            # Run Gemini API call in thread pool (it's synchronous)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._call_gemini(prompt, image),
            )
            
            if not result:
                return None
            
            q_type = result.get("type", "SAFE")
            answer_text = result.get("answer_text")
            bbox = result.get("bbox")
            
            if q_type == "SAFE" or not answer_text:
                return {"type": q_type, "action": None}
            
            # Calculate coordinates from bbox
            if bbox and len(bbox) == 4:
                ymin, xmin, ymax, xmax = bbox
                # Normalize to 0-1 range (bbox is 0-1000)
                center_x = (xmin + xmax) / 2 / 1000
                center_y = (ymin + ymax) / 2 / 1000
                
                if q_type == "MCQ":
                    return {
                        "type": "MCQ",
                        "action": "click",
                        "x": center_x,
                        "y": center_y,
                        "answer_text": answer_text,
                        "question": result.get("question"),
                    }
                elif q_type == "DESCRIPTIVE":
                    return {
                        "type": "DESCRIPTIVE",
                        "action": "type",
                        "x": center_x,
                        "y": center_y,
                        "text": answer_text,
                        "question": result.get("question"),
                        "marks": result.get("marks"),
                    }
            
            return {"type": q_type, "action": None}
        
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None
    
    def _call_gemini(self, prompt: str, image: Image.Image) -> Optional[dict]:
        """Synchronous Gemini API call."""
        try:
            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt, image],
            )
            
            raw_text = response.text.strip()
            
            # Clean up JSON if wrapped in markdown
            cleaned_text = raw_text
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned_text:
                cleaned_text = cleaned_text.split("```")[1].split("```")[0].strip()
            
            return json.loads(cleaned_text)
        
        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
            return None
    
    async def _analyze_with_import(
        self,
        image: Image.Image,
        question_type_hint: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Analyze using imported Scry modules."""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._get_gemini_response(
                    image,
                    enable_detailed_mode=ENABLE_DETAILED_MODE,
                    question_type_hint=question_type_hint,
                ),
            )
            
            if not result:
                return None
            
            q_type = result.get("type", "SAFE")
            answer_text = result.get("answer_text")
            bbox = result.get("bbox")
            
            if q_type == "SAFE" or not answer_text:
                return {"type": q_type, "action": None}
            
            # For MCQ, try to find text coordinates first
            if q_type == "MCQ":
                coords = await loop.run_in_executor(
                    None,
                    lambda: self._find_text_coordinates(image, answer_text),
                )
                if coords:
                    x, y = coords
                    # Normalize to 0-1 range
                    width, height = image.size
                    return {
                        "type": "MCQ",
                        "action": "click",
                        "x": x / width,
                        "y": y / height,
                        "answer_text": answer_text,
                    }
            
            # Fallback to bbox
            if bbox and len(bbox) == 4:
                ymin, xmin, ymax, xmax = bbox
                center_x = (xmin + xmax) / 2 / 1000
                center_y = (ymin + ymax) / 2 / 1000
                
                if q_type == "MCQ":
                    return {
                        "type": "MCQ",
                        "action": "click",
                        "x": center_x,
                        "y": center_y,
                        "answer_text": answer_text,
                    }
                elif q_type == "DESCRIPTIVE":
                    return {
                        "type": "DESCRIPTIVE",
                        "action": "type",
                        "x": center_x,
                        "y": center_y,
                        "text": answer_text,
                    }
            
            return {"type": q_type, "action": None}
        
        except Exception as e:
            logger.error(f"Import mode analysis error: {e}")
            return None
    
    async def _analyze_with_subprocess(
        self,
        image: Image.Image,
        question_type_hint: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Analyze using Scry as a subprocess."""
        # TODO: Implement subprocess communication
        # This would involve:
        # 1. Save image to temp file
        # 2. Run Scry analysis script
        # 3. Parse JSON output
        logger.warning("Subprocess mode not yet implemented")
        return None
