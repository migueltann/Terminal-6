"""TextMatcher: text helpers shared by the filtering rules.

Cleans text and checks whether a keyword (a preference or an avoid-list
term) matches a recommendation. Every method is static because the class
holds no data: it groups related helpers in one place (one job: matching
text) instead of leaving them as loose module functions.
"""

import re
from difflib import SequenceMatcher
from typing import Any


class TextMatcher:
    """Normalise text and match keywords against recommendation details."""

    @staticmethod
    def normalise(value: Any) -> str:
        """Convert text to lowercase and remove unnecessary symbols."""
        # "or ''" turns None into an empty string before converting.
        value = str(value or "").strip().lower()
        # Treat underscores and dashes as spaces: "street_market" -> "street market"
        value = re.sub(r"[_\-]+", " ", value)
        # Replace every other symbol (anything not a letter, digit or space)
        # with a space: "café & bar!" -> "café   bar "
        value = re.sub(r"[^\w\s]", " ", value)
        # split() + join() squeezes repeated spaces into one.
        return " ".join(value.split())

    @staticmethod
    def active_preferences(values: Any) -> list[str]:
        """Remove empty answers and placeholder preferences."""
        if not isinstance(values, list):
            return []

        # Drop answers like "", "Any" or "None" that mean "no preference".
        return [
            str(value).strip()
            for value in values
            if TextMatcher.normalise(value) not in {"", "any", "none"}
        ]

    @staticmethod
    def _as_text_list(value: Any) -> list[str]:
        """Convert a list into non-empty strings."""
        # The AI sometimes sends a single string or null instead of a list;
        # treat anything that is not a list as empty.
        if not isinstance(value, list):
            return []

        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    @staticmethod
    def _recommendation_text(item: dict) -> str:
        """Combine searchable recommendation information."""
        # Start with the main text fields of the recommendation...
        fields = [
            item.get("name", ""),
            item.get("category", ""),
            item.get("description", ""),
            item.get("location", ""),
        ]

        # ...then add every keyword list the AI might have included.
        for key in (
            "tags",
            "shopping_types",
            "shopping_interests",
            "interests",
            "activity_types",
            "themes",
            "keywords",
        ):
            fields.extend(TextMatcher._as_text_list(item.get(key, [])))

        # One long cleaned-up string that can be searched for any keyword.
        return TextMatcher.normalise(" ".join(str(field) for field in fields))

    @staticmethod
    def matches(preference: str, text: str) -> bool:
        """Check exact, word-based and approximate preference matches."""
        pref = TextMatcher.normalise(preference)
        searchable = TextMatcher.normalise(text)

        if not pref or not searchable:
            return False

        pref_words = pref.split()
        text_words = searchable.split()

        # 1. Exact phrase match. Spaces are added around both so only whole
        #    words match: "art" matches "street art" but not "party".
        if " " + pref + " " in " " + searchable + " ":
            return True

        # 2. Every word of the preference appears somewhere in the text,
        #    in any order: "food street" matches "street food market".
        if set(pref_words).issubset(text_words):
            return True

        # 3. Close spelling match, to allow small typos or plurals
        #    (e.g. "museums" vs "museum", or "restaurnt" vs "restaurant"). Skipped for short words, where a
        #    one-letter difference changes the meaning.
        if len(pref) >= 5:
            size = len(pref_words)

            # Slide a window the same number of words as the preference
            # across the text, and compare each window to the preference.
            for start in range(len(text_words) - size + 1):
                candidate = " ".join(text_words[start:start + size])

                # ratio() gives a similarity score from 0.0 to 1.0;
                # 0.88 or more counts as the same word.
                if SequenceMatcher(None, pref, candidate).ratio() >= 0.88:
                    return True

        return False

    @staticmethod
    def contains_term(item: dict, term: str) -> bool:
        """Check whether a term matches recommendation information."""
        return TextMatcher.matches(
            term,
            TextMatcher._recommendation_text(item),
        )