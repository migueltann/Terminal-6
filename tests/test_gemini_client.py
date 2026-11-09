
import os
import unittest
from unittest.mock import Mock, patch

from ai.gemini_client import GeminiClient


class TestGeminiClient(unittest.TestCase):

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("ai.gemini_client.time.sleep")
    @patch("ai.gemini_client.requests.post")
    def test_retry_then_success(self, mock_post, mock_sleep):
        """Retry a temporary error, then accept a valid response."""

        items = [
            {"type": category, "name": f"{category}-{i}"}
            for category in (
                "activity", "food", "accommodation", "shopping"
            )
            for i in range(15)
        ]

        busy_response = Mock()
        busy_response.status_code = 429
        busy_response.text = "Too many requests"

        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": __import__("json").dumps(items)}
                        ]
                    }
                }
            ]
        }

        mock_post.side_effect = [
            busy_response,
            success_response,
        ]

        client = GeminiClient(models=["test-model"])
        result = client.generate("Test prompt")

        self.assertEqual(len(result), 60)
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once_with(2)


    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("ai.gemini_client.requests.post")
    def test_model_fallback(self, mock_post):
        """Switch to another model when the first returns HTTP 404."""

        import json

        items = [
            {"type": category, "name": f"{category}-{i}"}
            for category in (
                "activity", "food", "accommodation", "shopping"
            )
            for i in range(15)
        ]

        unavailable_response = Mock()
        unavailable_response.status_code = 404
        unavailable_response.text = "Model not found"

        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": json.dumps(items)}
                        ]
                    }
                }
            ]
        }

        mock_post.side_effect = [
            unavailable_response,
            success_response,
        ]

        client = GeminiClient(
            models=["first-model", "second-model"]
        )

        result = client.generate("Test prompt")

        self.assertEqual(len(result), 60)
        self.assertEqual(mock_post.call_count, 2)

        self.assertIn(
            "first-model",
            mock_post.call_args_list[0].args[0]
        )

        self.assertIn(
            "second-model",
            mock_post.call_args_list[1].args[0]
        )


    
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("ai.gemini_client.requests.post")
    def test_retry_incomplete_recommendations(self, mock_post):
        """Retry when Gemini returns fewer than 60 recommendations."""

        import json

        incomplete_items = [
            {"name": "Tokyo Tower", "type": "activity"}
        ]

        valid_items = [
            {"type": category, "name": f"{category}-{i}"}
            for category in (
                "activity", "food", "accommodation", "shopping"
            )
            for i in range(15)
        ]

        def make_response(items):
            response = Mock()
            response.status_code = 200
            response.json.return_value = {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": json.dumps(items)}
                            ]
                        }
                    }
                ]
            }
            return response

        mock_post.side_effect = [
            make_response(incomplete_items),
            make_response(valid_items),
        ]

        client = GeminiClient(models=["test-model"])

        result = client.generate("Test prompt")

        self.assertEqual(len(result), 60)
        self.assertEqual(mock_post.call_count, 2)

    


if __name__ == "__main__":
    unittest.main()
