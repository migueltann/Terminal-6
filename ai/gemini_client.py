"""Sends prompts to Google's Gemini API and returns checked recommendations."""
import os
import time
from typing import Callable, Optional

import requests
from dotenv import load_dotenv

from ai.ai_response_validator import AIResponseValidator


class GeminiClient:
    """Communicate with Gemini and retry failed requests."""

    def __init__(
        self,
        validator: Optional[AIResponseValidator] = None,
        models: Optional[list[str]] = None,
        max_attempts: int = 3,
        request_timeout: float = 45,
    ):
        # Load GEMINI_API_KEY from the .env file into the environment.
        load_dotenv()

        # Checks that Gemini's answer has the right shape and fields.
        # "or" means: use the one passed in, otherwise create a new one.
        self._validator = validator or AIResponseValidator()

        # Models to try, in order. If one fails, the next is tried.
        self._models = models if models is not None else [
            "gemini-3.8-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite",
        ]

        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")

        # Tries per model before moving to the next model.
        self._max_attempts = max_attempts

        if request_timeout <= 0:
            raise ValueError("request_timeout must be greater than 0.")

        # A 15-item reply normally arrives in under 20 seconds. If Gemini
        # has not answered by this point it has usually stalled, so give
        # up and try the next model instead of waiting.
        self._request_timeout = request_timeout

    def _notify(
        self,
        notify: Optional[Callable[[str, str], None]],
        level: str,
        message: str,
    ) -> None:
        """Send progress messages if a callback is provided."""

        if notify is not None:
            notify(level, message)

    def generate(
        self,
        prompt: str,
        notify: Optional[Callable[[str, str], None]] = None,
        validator: Optional[Callable[[list[dict]], bool]] = None,
        category: Optional[str] = None,
    ) -> list[dict]:
        """Generate and validate recommendations using Gemini.

        Pass category when the prompt asks for one recommendation type
        only, so the response is checked for 15 items instead of 60.
        """

        api_key = os.getenv("GEMINI_API_KEY")

        # ValueError (not RuntimeError) tells FallbackClient that Gemini is
        # not set up, so it can move straight on to Groq.
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is missing."
            )

        # Remembered so the final error says what went wrong last.
        last_error = None

        # Outer loop: each model in turn.
        for model_name in self._models:
            self._notify(
                notify,
                "info",
                f"Trying Gemini model: {model_name}",
            )

            # Inner loop: retries on the same model.
            # "continue" = try this model again, "break" = next model.
            for attempt in range(self._max_attempts):
                url = (
                    "https://generativelanguage.googleapis.com/"
                    f"v1beta/models/{model_name}:generateContent"
                )

                try:
                    # Send the prompt to Gemini. The API key goes in a
                    # header, not the URL, so it does not appear in logs.
                    response = requests.post(
                        url,
                        headers={
                            "Content-Type": "application/json",
                            "x-goog-api-key": api_key,
                        },
                        json={
                            "contents": [
                                {"parts": [{"text": prompt}]}
                            ],
                            # Ask Gemini to reply with JSON only.
                            "generationConfig": {
                                "response_mime_type": "application/json"
                            },
                        },
                        timeout=self._request_timeout,
                    )

                # No reply within request_timeout: move to the next model.
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

                # 200 = success: check the answer is usable.
                if response.status_code == 200:
                    try:
                        recommendations = (
                            self._validator.parse_gemini_response(
                                response, category
                            )
                        )

                        if (
                            validator is not None
                            and not validator(recommendations)
                        ):
                            raise RuntimeError(
                                "Gemini returned no usable recommendations."
                            )

                    # The answer was broken (bad JSON, wrong item count...).
                    # Asking the same model again usually fixes it.
                    except RuntimeError as err:
                        last_error = err

                        if attempt < self._max_attempts - 1:
                            self._notify(
                                notify,
                                "warning",
                                f"{model_name} returned malformed output. "
                                "Retrying...",
                            )
                            continue

                        self._notify(
                            notify,
                            "warning",
                            f"{model_name} kept returning malformed output.",
                        )
                        break

                    self._notify(
                        notify,
                        "info",
                        f"Gemini succeeded using {model_name}.",
                    )

                    return recommendations

                # Temporary problems worth waiting for:
                # 429 = too many requests, 5xx = Gemini's servers are busy.
                # [:300] keeps only the start of a long error message.
                if response.status_code in {429, 500, 502, 503, 504}:
                    last_error = RuntimeError(
                        f"HTTP {response.status_code}: "
                        f"{response.text[:300]}"
                    )

                    if attempt < self._max_attempts - 1:
                        # Exponential backoff: wait 2s, then 4s, then 8s...
                        # giving the server more time after each failure.
                        wait_time = 2 ** (attempt + 1)

                        self._notify(
                            notify,
                            "warning",
                            f"{model_name} is busy. "
                            f"Retrying in {wait_time} seconds...",
                        )

                        time.sleep(wait_time)
                        continue

                    self._notify(
                        notify,
                        "warning",
                        f"{model_name} is still unavailable.",
                    )
                    break

                # 404 = this model does not exist (e.g. Google retired it).
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

                # Anything else (e.g. 401/403 = bad API key): record it
                # and try the next model.
                last_error = RuntimeError(
                    f"Gemini API returned HTTP {response.status_code}: "
                    f"{response.text[:300]}"
                )
                break

        # Every model failed. FallbackClient catches this and tries Groq.
        raise RuntimeError(
            "All Gemini models failed. "
            f"Last error: {last_error}"
        )
