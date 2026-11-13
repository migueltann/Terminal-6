import json
import os
import unittest
from unittest.mock import Mock, patch

import requests

from ai.fallback_client import FallbackClient
from ai.groq_client import DEFAULT_GROQ_MODELS, GroqClient


def make_food_items():
    """Create 15 valid food recommendations."""
    return [
        {
            "name": f"food-{i}",
            "type": "food",
            "category": "Restaurant",
            "estimated_cost_sgd": 20,
            "location": "Tokyo",
            "environment": "Indoor",
            "description": "A sample recommendation",
            "tags": [],
            "transport_options": ["transit"],
            "dietary_tags": ["none"],
        }
        for i in range(15)
    ]


def groq_response(status_code=200, content=None, text="", headers=None):
    """Build a fake Groq HTTP response."""
    response = Mock()
    response.status_code = status_code
    response.text = text
    response.headers = headers or {}
    response.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    return response


def wrapped(items):
    """Groq JSON mode returns an object holding the array."""
    return json.dumps({"recommendations": items})


@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
class TestGroqClient(unittest.TestCase):

    @patch("ai.groq_client.requests.post")
    def test_success_unwraps_recommendations(self, mock_post):
        mock_post.return_value = groq_response(
            content=wrapped(make_food_items())
        )

        result = GroqClient(models=["test-model"]).generate(
            "Test prompt", category="food"
        )

        self.assertEqual(len(result), 15)
        body = mock_post.call_args.kwargs["json"]
        self.assertEqual(body["model"], "test-model")
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertIn("recommendations", body["messages"][0]["content"])
        self.assertEqual(
            mock_post.call_args.kwargs["headers"]["Authorization"],
            "Bearer test-key",
        )

    @patch("ai.groq_client.time.sleep")
    @patch("ai.groq_client.requests.post")
    def test_rate_limit_uses_retry_after(self, mock_post, mock_sleep):
        mock_post.side_effect = [
            groq_response(429, text="rate limited",
                          headers={"retry-after": "3"}),
            groq_response(content=wrapped(make_food_items())),
        ]

        result = GroqClient(models=["test-model"]).generate(
            "Test prompt", category="food"
        )

        self.assertEqual(len(result), 15)
        mock_sleep.assert_called_once_with(3.0)

    @patch("ai.groq_client.time.sleep")
    @patch("ai.groq_client.requests.post")
    def test_retry_after_is_capped(self, mock_post, mock_sleep):
        mock_post.side_effect = [
            groq_response(429, headers={"retry-after": "600"}),
            groq_response(content=wrapped(make_food_items())),
        ]

        GroqClient(models=["m"], max_retry_wait=20).generate(
            "Test prompt", category="food"
        )

        mock_sleep.assert_called_once_with(20)

    @patch("ai.groq_client.requests.post")
    def test_json_validate_failed_is_retried(self, mock_post):
        mock_post.side_effect = [
            groq_response(400, text='{"error":{"code":"json_validate_failed"}}'),
            groq_response(content=wrapped(make_food_items())),
        ]

        result = GroqClient(models=["m"]).generate(
            "Test prompt", category="food"
        )

        self.assertEqual(len(result), 15)
        self.assertEqual(mock_post.call_count, 2)

    @patch("ai.groq_client.requests.post")
    def test_wrong_item_count_is_retried(self, mock_post):
        mock_post.side_effect = [
            groq_response(content=wrapped(make_food_items()[:10])),
            groq_response(content=wrapped(make_food_items())),
        ]

        result = GroqClient(models=["m"]).generate(
            "Test prompt", category="food"
        )

        self.assertEqual(len(result), 15)

    @patch("ai.groq_client.requests.post")
    def test_timeout_moves_to_next_model(self, mock_post):
        mock_post.side_effect = [
            requests.Timeout("read timed out"),
            groq_response(content=wrapped(make_food_items())),
        ]

        # Force the model order so the test checks only the timeout.
        with patch.object(
            GroqClient, "_models_for", return_value=["slow", "fast"]
        ):
            GroqClient(models=["slow", "fast"]).generate(
                "Test prompt", category="food"
            )

        self.assertEqual(
            mock_post.call_args_list[1].kwargs["json"]["model"], "fast"
        )

    @patch("ai.groq_client.requests.post")
    def test_all_models_failing_raises(self, mock_post):
        mock_post.return_value = groq_response(404, text="model not found")

        with self.assertRaises(RuntimeError):
            GroqClient(models=["a", "b"]).generate("Test prompt")

        self.assertEqual(mock_post.call_count, 2)

    def test_categories_are_spread_across_models(self):
        client = GroqClient(models=["big", "small"])

        self.assertEqual(client._models_for("activity"), ["big", "small"])
        self.assertEqual(client._models_for("food"), ["small", "big"])
        self.assertEqual(
            client._models_for("accommodation"), ["big", "small"]
        )
        self.assertEqual(client._models_for("shopping"), ["small", "big"])
        self.assertEqual(client._models_for(None), ["big", "small"])

    @patch("ai.groq_client.requests.post")
    def test_food_request_starts_on_second_model(self, mock_post):
        mock_post.return_value = groq_response(
            content=wrapped(make_food_items())
        )

        GroqClient(models=["big", "small"]).generate(
            "Test prompt", category="food"
        )

        self.assertEqual(
            mock_post.call_args.kwargs["json"]["model"], "small"
        )

    def test_models_can_be_set_in_env(self):
        with patch.dict(os.environ, {"GROQ_MODELS": " x/one , x/two "}):
            client = GroqClient()

        self.assertEqual(client._models, ["x/one", "x/two"])

    def test_default_models_used_without_env(self):
        with patch.dict(os.environ, {"GROQ_MODELS": ""}):
            client = GroqClient()

        self.assertEqual(client._models, DEFAULT_GROQ_MODELS)


class TestGroqClientWithoutKey(unittest.TestCase):

    @patch("ai.groq_client.load_dotenv")
    @patch("ai.groq_client.requests.post")
    def test_missing_key_raises_value_error(self, mock_post, _dotenv):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                GroqClient().generate("Test prompt")

        mock_post.assert_not_called()


class FakeProvider:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0

    def generate(self, prompt, notify=None, validator=None, category=None):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


class TestFallbackClient(unittest.TestCase):

    def test_first_provider_success_skips_backup(self):
        primary = FakeProvider(result=["gemini"])
        backup = FakeProvider(result=["groq"])

        result = FallbackClient(
            [("Gemini", primary), ("Groq", backup)]
        ).generate("p")

        self.assertEqual(result, ["gemini"])
        self.assertEqual(backup.calls, 0)

    def test_switches_to_backup_when_primary_fails(self):
        messages = []
        primary = FakeProvider(error=RuntimeError("HTTP 503"))
        backup = FakeProvider(result=["groq"])

        result = FallbackClient(
            [("Gemini", primary), ("Groq", backup)]
        ).generate("p", notify=lambda level, msg: messages.append(msg))

        self.assertEqual(result, ["groq"])
        self.assertIn("Gemini failed. Switching to Groq...", messages)

    def test_missing_key_on_primary_uses_backup(self):
        primary = FakeProvider(error=ValueError("GEMINI_API_KEY missing"))
        backup = FakeProvider(result=["groq"])

        result = FallbackClient(
            [("Gemini", primary), ("Groq", backup)]
        ).generate("p")

        self.assertEqual(result, ["groq"])

    def test_all_providers_failing_raises_with_every_error(self):
        client = FallbackClient([
            ("Gemini", FakeProvider(error=RuntimeError("HTTP 503"))),
            ("Groq", FakeProvider(error=ValueError("GROQ_API_KEY is missing"))),
        ])

        with self.assertRaises(RuntimeError) as ctx:
            client.generate("p")

        message = str(ctx.exception)
        self.assertIn("All AI providers failed", message)
        self.assertIn("Gemini: HTTP 503", message)
        self.assertIn("Groq: GROQ_API_KEY is missing", message)

    def test_needs_at_least_one_provider(self):
        with self.assertRaises(ValueError):
            FallbackClient([])


if __name__ == "__main__":
    unittest.main()
