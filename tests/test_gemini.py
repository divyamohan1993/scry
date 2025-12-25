import json
from unittest.mock import MagicMock

from src.gemini import get_gemini_response


class TestGeminiResponse:

    def test_get_gemini_response_valid_mcq(self, mock_gemini_client):
        """Test simple valid JSON response for MCQ."""
        # Setup wrong response structure
        # The client.models.generate_content return object structure depends on the library version
        # Assuming response.text is the access method as used in source code

        mock_response = MagicMock()
        expected_dict = {
            "type": "MCQ",
            "question": "What is 2+2?",
            "answer_text": "4",
            "bbox": [100, 100, 200, 200],
        }
        mock_response.text = json.dumps(expected_dict)

        mock_gemini_client.models.generate_content.return_value = mock_response

        # Image mock (using bytes or generic object)
        image_mock = MagicMock()

        result = get_gemini_response(image_mock)

        assert result is not None
        assert result["type"] == "MCQ"
        assert result["answer_text"] == "4"
        assert result["bbox"] == [100, 100, 200, 200]

    def test_get_gemini_response_with_markdown_blocks(self, mock_gemini_client):
        """Test response wrapped in markdown code blocks."""
        mock_response = MagicMock()
        data = {"type": "DESCRIPTIVE", "answer_text": "It is a number."}
        mock_response.text = f"```json\n{json.dumps(data)}\n```"
        mock_gemini_client.models.generate_content.return_value = mock_response

        result = get_gemini_response(MagicMock())

        assert result["type"] == "DESCRIPTIVE"
        assert result["answer_text"] == "It is a number."

    def test_get_gemini_response_malformed_json_triggers_fallback(
        self, mock_gemini_client, mocker
    ):
        """Test that invalid JSON triggers the fallback mechanism."""
        # First call returns garbage
        bad_response = MagicMock()
        bad_response.text = "This is not json."

        # Second call (fallback) returns valid json
        good_response = MagicMock()
        good_response.text = json.dumps({"type": "SAFE"})

        # We need to mock the SIDE_EFFECT of generate_content to return different values on consecutive calls
        # Note: The code calls generate_content with different models.
        # The mock is on the client instance, so we can check call args or use side_effect.

        mock_gemini_client.models.generate_content.side_effect = [
            bad_response,
            good_response,
        ]

        result = get_gemini_response(MagicMock())

        assert result is not None
        assert result["type"] == "SAFE"

        # Verify calls
        # 1. Primary Model
        call_args_list = mock_gemini_client.models.generate_content.call_args_list
        assert len(call_args_list) == 2
        assert "gemini-3-flash-preview" in call_args_list[0].kwargs["model"]
        assert "gemini-2.5-flash" in call_args_list[1].kwargs["model"]

    def test_get_gemini_response_api_exception_triggers_fallback(
        self, mock_gemini_client
    ):
        """Test availability exception triggers fallback."""
        # First call raises Exception
        mock_gemini_client.models.generate_content.side_effect = [
            Exception("API Error"),
            MagicMock(text='{"type":"SAFE"}'),
        ]

        result = get_gemini_response(MagicMock())

        assert result["type"] == "SAFE"

    def test_get_gemini_response_total_failure(self, mock_gemini_client):
        """Test both primary and fallback failing."""
        mock_gemini_client.models.generate_content.side_effect = Exception("All Failed")

        result = get_gemini_response(MagicMock())
        assert result is None
