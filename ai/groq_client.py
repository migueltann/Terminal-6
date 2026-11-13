import os
import time
from typing import Callable, Optional

import requests
from dotenv import load_dotenv

from ai.ai_response_validator import AIResponseValidator


# Groq's API uses the same request/response format as OpenAI's
# "chat completions" API.
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Groq retires models often (the Llama models were removed in August
# 2026). Override with GROQ_MODELS=model-a,model-b in .env if these go.
DEFAULT_GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]

# Groq's JSON mode must return an object, not a bare array, so the
# prompt asks for the array to be wrapped. The validator unwraps it.
JSON_OBJECT_INSTRUCTION = """

    OUTPUT FORMAT OVERRIDE:
    Wrap the JSON array in a JSON object like this:
    {"recommendations": [ ...recommendation objects... ]}
    Return only that JSON object.
"""

# The free tier allows about 8,000 tokens per minute *per model*, and one
# category uses about 3,000-3,500. Four categories on one model go over
# the limit, so each category starts on a different model in turn:
# activity/accommodation -> first model, food/shopping -> second model.
CATEGORY_ORDER = ("activity", "food", "accommodation", "shopping")


class GroqClient:
    """Communicate with Groq, used as a backup when Gemini fails.

    It has the same generate() method as GeminiClient, so FallbackClient
    and AIManager can use either one without knowing which it is.
    """

    def __init__(
        self,
        validator: Optional[AIResponseValidator] = None,
        models: Optional[list[str]] = None,
        max_attempts: int = 3,
        request_timeout: float = 45,
        max_retry_wait: float = 20,
    ):
        # Load GROQ_API_KEY (and GROQ_MODELS, if set) from the .env file.
        load_dotenv()

        # The same validator as Gemini, so Groq's answers are checked
        # with the same rules (15 items, right category, all fields).
        self._validator = validator or AIResponseValidator()

        # Model list: models passed in > GROQ_MODELS in .env > defaults.
        if models is None:
            env_models = os.getenv("GROQ_MODELS", "")
            models = [
                name.strip() for name in env_models.split(",")
                if name.strip()
            ] or list(DEFAULT_GROQ_MODELS)

        self._models = models

        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")

        if request_timeout <= 0:
            raise ValueError("request_timeout must be greater than 0.")

        # Tries per model before moving to the next model.
        self._max_attempts = max_attempts
        # Seconds to wait for one reply before giving up on that model.
        self._request_timeout = request_timeout
        # Longest pause allowed after a "busy" (rate-limited) reply.
        self._max_retry_wait = max_retry_wait

    def _notify(
        self,
        notify: Optional[Callable[[str, str], None]],
        level: str,
        message: str,
    ) -> None:
        """Send progress messages if a callback is provided."""

        if notify is not None:
            notify(level, message)

    def _retry_wait(self, response, attempt: int) -> float:
        """Use Groq's retry-after header if given, else back off."""

        # When rate-limited, Groq says how many seconds to wait in the
        # "retry-after" header. If it is missing, wait 2s, then 4s, ...
        # Either way, never wait longer than max_retry_wait.
        try:
            wait = float(response.headers.get("retry-after", ""))
        except (TypeError, ValueError, AttributeError):
            wait = 2 ** (attempt + 1)

        return max(0.0, min(wait, self._max_retry_wait))

    def _models_for(self, category: Optional[str]) -> list[str]:
        """Rotate the model list so categories share the token budget."""

        # No category, or only one model: nothing to rotate.
        if category not in CATEGORY_ORDER or len(self._models) < 2:
            return list(self._models)

        # With 2 models: activity (0) and accommodation (2) start on
        # model 0, food (1) and shopping (3) start on model 1. Each list
        # still contains every model, so the other one is the fallback.
        # e.g. food -> ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
        start = CATEGORY_ORDER.index(category) % len(self._models)
        return self._models[start:] + self._models[:start]

    def generate(
        self,
        prompt: str,
        notify: Optional[Callable[[str, str], None]] = None,
        validator: Optional[Callable[[list[dict]], bool]] = None,
        category: Optional[str] = None,
    ) -> list[dict]:
        """Generate and validate recommendations using Groq.

        Tries each model in turn, up to max_attempts times per model,
        and returns the first valid answer. Raises RuntimeError if every
        model fails, so FallbackClient / AIManager can react.
        """

        # Read the key on every call (not in __init__) so a missing key
        # only fails when Groq is actually needed. A ValueError here
        # tells FallbackClient that Groq is not set up.
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable is missing."
            )

        # Remembered so the final error says what went wrong last.
        last_error = None

        # Outer loop: each model, starting with this category's model.
        for model_name in self._models_for(category):
            self._notify(
                notify,
                "info",
                f"Trying Groq model: {model_name}",
            )

            # Inner loop: retries on the same model.
            # "continue" = try this model again, "break" = next model.
            for attempt in range(self._max_attempts):
                try:
                    # Send the prompt. Groq authenticates with a
                    # "Bearer" token (Gemini uses an x-goog-api-key
                    # header instead).
                    response = requests.post(
                        GROQ_URL,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {api_key}",
                        },
                        json={
                            "model": model_name,
                            # Chat format: a list of messages. We send
                            # one "user" message containing the prompt.
                            "messages": [
                                {
                                    "role": "user",
                                    "content": prompt
                                    + JSON_OBJECT_INSTRUCTION,
                                }
                            ],
                            # JSON mode: Groq checks the reply is valid
                            # JSON before sending it back.
                            "response_format": {"type": "json_object"},
                            # gpt-oss models "think" before answering;
                            # low effort keeps replies fast and small.
                            "reasoning_effort": "low",
                        },
                        timeout=self._request_timeout,
                    )

                # No reply within request_timeout: the model has probably
                # stalled, so stop waiting and move to the next model.
                except requests.Timeout as err:
                    last_error = err
                    self._notify(
                        notify,
                        "warning",
                        f"{model_name} did not respond within "
                        f"{self._request_timeout:g} seconds.",
                    )
                    break

                # Any other network problem (no internet, DNS, etc.).
                except requests.RequestException as err:
                    last_error = err
                    self._notify(
                        notify,
                        "warning",
                        f"{model_name} request failed: {err}",
                    )
                    break

                # Set to True when the model answered but the answer
                # could not be used; those are worth retrying.
                malformed = False

                # 200 = success. The answer text is in
                # choices[0].message.content (OpenAI-style response).
                if response.status_code == 200:
                    try:
                        content = (
                            response.json()["choices"][0]
                            ["message"]["content"]
                        )
                    except (ValueError, KeyError, IndexError, TypeError):
                        content = None

                    # Parse the JSON and check it: at least 15 complete
                    # items of this category (the first 15 are kept).
                    try:
                        recommendations = (
                            self._validator.parse_recommendation_text(
                                content, category
                            )
                        )

                        if (
                            validator is not None
                            and not validator(recommendations)
                        ):
                            raise RuntimeError(
                                "Groq returned no usable recommendations."
                            )

                    # Validation failed, e.g. only 14 items or bad JSON.
                    except RuntimeError as err:
                        last_error = err
                        malformed = True

                    # "else" runs only if the try block raised nothing:
                    # the answer is valid, so return it.
                    else:
                        self._notify(
                            notify,
                            "info",
                            f"Groq succeeded using {model_name}.",
                        )
                        return recommendations

                # Groq answers 400 json_validate_failed when the model
                # wrote broken JSON. Asking again usually fixes it.
                elif (
                    response.status_code == 400
                    and "json_validate_failed" in response.text
                ):
                    last_error = RuntimeError(
                        "Groq returned invalid JSON (json_validate_failed)."
                    )
                    malformed = True

                # Unusable answer: ask the same model again, and after
                # max_attempts tries move on to the next model.
                if malformed:
                    if attempt < self._max_attempts - 1:
                        self._notify(
                            notify,
                            "warning",
                            f"{model_name} returned malformed output "
                            f"({str(last_error)[:100]}). Retrying...",
                        )
                        continue

                    self._notify(
                        notify,
                        "warning",
                        f"{model_name} kept returning malformed output.",
                    )
                    break

                # Temporary problems worth waiting for:
                # 429 = rate limit (e.g. the free tier's 8,000 tokens
                # per minute), 5xx = Groq's servers are busy or down.
                if response.status_code in {429, 500, 502, 503, 504}:
                    last_error = RuntimeError(
                        f"HTTP {response.status_code}: "
                        f"{response.text[:300]}"
                    )

                    if attempt < self._max_attempts - 1:
                        wait_time = self._retry_wait(response, attempt)

                        self._notify(
                            notify,
                            "warning",
                            f"{model_name} is busy. "
                            f"Retrying in {wait_time:g} seconds...",
                        )

                        time.sleep(wait_time)
                        continue

                    self._notify(
                        notify,
                        "warning",
                        f"{model_name} is still unavailable.",
                    )
                    break

                # 404 = this model does not exist (e.g. Groq retired it).
                # Retrying will not help, so go to the next model.
                if response.status_code == 404:
                    last_error = RuntimeError(
                        f"HTTP 404: {response.text[:300]}"
                    )
                    self._notify(
                        notify,
                        "warning",
                        f"{model_name} is not available.",
                    )
                    break

                # Anything else (e.g. 401 = bad API key): record it and
                # try the next model.
                last_error = RuntimeError(
                    f"Groq API returned HTTP {response.status_code}: "
                    f"{response.text[:300]}"
                )
                break

        # Every model failed. FallbackClient catches this RuntimeError.
        raise RuntimeError(
            "All Groq models failed. "
            f"Last error: {last_error}"
        )
