
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
    ):
        load_dotenv()

        self._validator = validator or AIResponseValidator()

        self._models = models if models is not None else [
            "gemini-3.8-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite",
        ]

        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")

        self._max_attempts = max_attempts

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
    ) -> list[dict]:
        """Generate and validate recommendations using Gemini."""

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is missing."
            )

        last_error = None

        for model_name in self._models:
            self._notify(
                notify,
                "info",
                f"Trying Gemini model: {model_name}",
            )

            for attempt in range(self._max_attempts):
                url = (
                    "https://generativelanguage.googleapis.com/"
                    f"v1beta/models/{model_name}:generateContent"
                )

                try:
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
                            "generationConfig": {
                                "response_mime_type": "application/json"
                            },
                        },
                        timeout=100,
                    )

                except requests.RequestException as err:
                    last_error = err
                    break

                if response.status_code == 200:
                    try:
                        recommendations = (
                            self._validator.parse_gemini_response(response)
                        )

                        if (
                            validator is not None
                            and not validator(recommendations)
                        ):
                            raise RuntimeError(
                                "Gemini returned no usable recommendations."
                            )

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

                if response.status_code in {429, 500, 502, 503, 504}:
                    last_error = RuntimeError(
                        f"HTTP {response.status_code}: "
                        f"{response.text[:300]}"
                    )

                    if attempt < self._max_attempts - 1:
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

                last_error = RuntimeError(
                    f"Gemini API returned HTTP {response.status_code}: "
                    f"{response.text[:300]}"
                )
                break

        raise RuntimeError(
            "All Gemini models failed. "
            f"Last error: {last_error}"
        )
