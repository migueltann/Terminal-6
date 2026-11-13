
import os
import unittest
from unittest.mock import Mock, patch

from ai.gemini_client import GeminiClient


def make_valid_items():
    """Create 60 valid recommendations for testing GeminiClient."""
    return [
        {
            "name": f"{category}-{i}",
            "type": category,
            "category": "General",
            "estimated_cost_sgd": 30,
            "location": "Singapore",
            "environment": "Indoor",
            "description": "A sample recommendation",
            "tags": [],
            "transport_options": ["transit"],
            "dietary_tags": ["halal"],
        }
        for category in (
            "activity", "food", "accommodation", "shopping"
        )
        for i in range(15)
    ]


class TestGeminiClient(unittest.TestCase):

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("ai.gemini_client.time.sleep")
    @patch("ai.gemini_client.requests.post")
    def test_retry_then_success(self, mock_post, mock_sleep):
        """Retry a temporary error, then accept a valid response."""

        items = make_valid_items()

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

        items = make_valid_items()

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

        valid_items = make_valid_items()

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

    


    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("ai.gemini_client.requests.post")
    def test_generate_single_category(self, mock_post):
        """Accept 15 items when a category is requested."""

        import json

        food_items = [
            item for item in make_valid_items()
            if item["type"] == "food"
        ]

        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps(food_items)}]}}
            ]
        }
        mock_post.return_value = success_response

        client = GeminiClient(models=["test-model"])
        result = client.generate("Test prompt", category="food")

        self.assertEqual(len(result), 15)
        self.assertEqual(mock_post.call_count, 1)


    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("ai.gemini_client.requests.post")
    def test_timeout_moves_to_next_model(self, mock_post):
        """A stalled request is reported and the next model is tried."""

        import json

        import requests

        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps(make_valid_items())}]}}
            ]
        }
        mock_post.side_effect = [
            requests.Timeout("read timed out"),
            success_response,
        ]
        messages = []

        client = GeminiClient(
            models=["slow-model", "fast-model"],
            request_timeout=30,
        )
        result = client.generate(
            "Test prompt",
            notify=lambda level, message: messages.append(message),
        )

        self.assertEqual(len(result), 60)
        self.assertEqual(mock_post.call_args_list[0].kwargs["timeout"], 30)
        self.assertIn("fast-model", mock_post.call_args_list[1].args[0])
        self.assertIn(
            "slow-model did not respond within 30 seconds.", messages
        )

    def test_invalid_request_timeout_is_rejected(self):
        with self.assertRaises(ValueError):
            GeminiClient(request_timeout=0)


if __name__ == "__main__":
    unittest.main()
