
from typing import Any, Callable, Optional

from ai.prompt_builder import PromptBuilder
from ai.gemini_client import GeminiClient


class AIManager:
    """Coordinate prompt building and AI recommendation generation."""

    def __init__(
        self,
        prompt_builder: Optional[PromptBuilder] = None,
        gemini_client: Optional[GeminiClient] = None,
    ):
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._gemini_client = gemini_client or GeminiClient()

    def generate_recommendations(
        self,
        destination: str,
        user_inputs: Optional[dict] = None,
        notify: Optional[Callable[[str, str], None]] = None,
        validator: Optional[Callable[[list[dict]], Any]] = None,
    ) -> list[dict]:
        """Build a prompt and request recommendations from Gemini."""

        if not isinstance(destination, str) or not destination.strip():
            raise ValueError("Destination cannot be empty.")

        prompt = self._prompt_builder.build(
            destination.strip(),
            user_inputs,
        )

        recommendations = self._gemini_client.generate(
            prompt,
            notify=notify,
            validator=validator,
        )

        return recommendations
