
import json
from typing import Any


class AIResponseValidator:
    """Parse and validate recommendation responses from Gemini."""

    def clean_json_response(self, content: str) -> str:
        """Remove Markdown JSON fences if Gemini includes them."""

        content = content.strip()

        if content.startswith("```"):
            lines = content.splitlines()[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            content = "\n".join(lines).strip()

        return content

    
    
    def validate_response_schema(self, items: Any) -> list[dict]:
        """Check that Gemini returns exactly 60 recommendations."""

        # 1. Check whether the response is a list
        if not isinstance(items, list):
            raise RuntimeError(
                "Gemini returned an unexpected recommendation structure."
            )

        # 2. Check whether the list is empty
        if not items:
            raise RuntimeError(
                "Gemini returned an empty recommendation list."
            )

        # 3. Check whether there are exactly 60 recommendations
        if len(items) != 60:
            raise RuntimeError(
                f"Gemini returned {len(items)} recommendations instead of 60."
            )

        # 4. Check whether every recommendation is a dictionary
        if not all(isinstance(item, dict) for item in items):
            raise RuntimeError(
                "Gemini returned items that are not JSON objects."
            )

        # 5. Check whether each category contains exactly 15
        required_categories = {
            "activity": 15,
            "food": 15,
            "accommodation": 15,
            "shopping": 15,
        }

        for category, expected_count in required_categories.items():
            actual_count = sum(
                1 for item in items
                if item.get("type") == category
            )

            if actual_count != expected_count:
                raise RuntimeError(
                    f"Gemini returned {actual_count} {category} recommendations "
                    f"instead of {expected_count}."
                )

        # 6. Return the validated recommendations
        return items



    def parse_gemini_response(self, response: Any) -> list[dict]:
        """Extract recommendations from a Gemini API response."""

        try:
            response_data = response.json()
        except ValueError as err:
            raise RuntimeError(
                f"Gemini response was not valid JSON: {err}"
            ) from err

        if not isinstance(response_data, dict):
            raise RuntimeError(
                "Gemini response format was unexpected."
            )

        candidates = response_data.get("candidates", [])

        if not candidates:
            raise RuntimeError("Gemini returned no candidates.")

        try:
            content = candidates[0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as err:
            raise RuntimeError(
                "Gemini response format was unexpected."
            ) from err

        try:
            parsed = json.loads(self.clean_json_response(content))
        except json.JSONDecodeError as err:
            raise RuntimeError(
                f"Gemini returned invalid JSON: {err}"
            ) from err

        if isinstance(parsed, list):
            return self.validate_response_schema(parsed)

        if isinstance(parsed, dict):
            for key in ("recommendations", "items"):
                if isinstance(parsed.get(key), list):
                    return self.validate_response_schema(parsed[key])

        raise RuntimeError(
            "Gemini returned an unexpected JSON structure."
        )
