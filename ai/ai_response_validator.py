
import json
from typing import Any, Optional


# How many recommendations of each type a full response must contain.
FULL_DISTRIBUTION = {
    "activity": 15,
    "food": 15,
    "accommodation": 15,
    "shopping": 15,
}


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

    
    
    def validate_response_schema(
        self,
        items: Any,
        category: Optional[str] = None,
    ) -> list[dict]:
        """Check that the AI returned the expected recommendations.

        Without a category, expect exactly 60 recommendations (15 per type).

        With a category, expect at least 15 complete recommendations of
        that type. Models often write one or two extra, so the first 15
        are kept instead of rejecting the whole answer and asking again.
        """

        if category is None:
            required_categories = dict(FULL_DISTRIBUTION)
        elif category in FULL_DISTRIBUTION:
            required_categories = {category: FULL_DISTRIBUTION[category]}
        else:
            raise ValueError(
                f"Unknown recommendation category: {category}"
            )

        expected_total = sum(required_categories.values())

        required_fields = {
            "name",
            "type",
            "category",
            "estimated_cost_sgd",
            "location",
            "environment",
            "description",
        }

        # 1. Check whether the response is a list
        if not isinstance(items, list):
            raise RuntimeError(
                "AI returned an unexpected recommendation structure."
            )

        # 2. Check whether the list is empty
        if not items:
            raise RuntimeError(
                "AI returned an empty recommendation list."
            )

        # 2b. Single category: keep the first 15 complete items of that type
        if category is not None:
            usable = [
                item for item in items
                if isinstance(item, dict)
                and item.get("type") == category
                and required_fields <= item.keys()
            ]

            if len(usable) < expected_total:
                raise RuntimeError(
                    f"AI returned {len(usable)} complete {category} "
                    f"recommendations instead of {expected_total}."
                )

            return usable[:expected_total]

        # 3. Check whether there are the expected number of recommendations
        if len(items) != expected_total:
            raise RuntimeError(
                f"AI returned {len(items)} recommendations "
                f"instead of {expected_total}."
            )

        # 4. Check whether every recommendation is a dictionary
        if not all(isinstance(item, dict) for item in items):
            raise RuntimeError(
                "AI returned items that are not JSON objects."
            )

        # 5. Check whether each category contains exactly 15
        for item_type, expected_count in required_categories.items():
            actual_count = sum(
                1 for item in items
                if item.get("type") == item_type
            )

            if actual_count != expected_count:
                raise RuntimeError(
                    f"AI returned {actual_count} {item_type} recommendations "
                    f"instead of {expected_count}."
                )

        # 6. Check that every recommendation has the required fields
        for index, item in enumerate(items, start=1):
            missing_fields = required_fields - item.keys()

            if missing_fields:
                raise RuntimeError(
                    f"Recommendation {index} is missing required fields: "
                    f"{', '.join(sorted(missing_fields))}"
                )

        # 7. Return the validated recommendations
        return items




    def parse_gemini_response(
        self,
        response: Any,
        category: Optional[str] = None,
    ) -> list[dict]:
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

        return self.parse_recommendation_text(content, category)

    def parse_recommendation_text(
        self,
        content: Any,
        category: Optional[str] = None,
    ) -> list[dict]:
        """Parse and validate the JSON text written by any AI model.

        Accepts either a JSON array of recommendations or an object
        holding the array under "recommendations" or "items".
        """

        if not isinstance(content, str):
            raise RuntimeError("AI response contained no text.")

        try:
            parsed = json.loads(self.clean_json_response(content))
        except json.JSONDecodeError as err:
            raise RuntimeError(
                f"AI returned invalid JSON: {err}"
            ) from err

        if isinstance(parsed, list):
            return self.validate_response_schema(parsed, category)

        if isinstance(parsed, dict):
            for key in ("recommendations", "items"):
                if isinstance(parsed.get(key), list):
                    return self.validate_response_schema(
                        parsed[key], category
                    )

        raise RuntimeError(
            "AI returned an unexpected JSON structure."
        )
