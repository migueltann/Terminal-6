
"""Shared helper functions for recommendation filtering."""

import re
from difflib import SequenceMatcher
from typing import Any


# When the user gave no preferences for a category, this many of the
# cheapest affordable items in it are marked as top picks.
CHEAPEST_TOP_PICK_COUNT = 3


def _normalise(value: Any) -> str:
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


def _active_preferences(values: Any) -> list[str]:
    """Remove empty answers and placeholder preferences."""
    if not isinstance(values, list):
        return []

    # Drop answers like "", "Any" or "None" that mean "no preference".
    return [
        str(value).strip()
        for value in values
        if _normalise(value) not in {"", "any", "none"}
    ]


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
        fields.extend(_as_text_list(item.get(key, [])))

    # One long cleaned-up string that can be searched for any keyword.
    return _normalise(" ".join(str(field) for field in fields))


def _preference_matches_text(preference: str, text: str) -> bool:
    """Check exact, word-based and approximate preference matches."""
    pref = _normalise(preference)
    searchable = _normalise(text)

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
    #    ("musuem" vs "museum"). Skipped for short words, where a
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


def matches_shopping_preference(item: dict, preference: str) -> bool:
    """Match shopping preferences against recommendation information."""
    # Shopping uses its own text: the shop types and what can be bought
    # there, plus the tags, name, category and description.
    shopping_text = " ".join(
        _as_text_list(item.get("shopping_types", []))
        + _as_text_list(item.get("shopping_interests", []))
        + _as_text_list(item.get("tags", []))
        + [
            str(item.get("name", "")),
            str(item.get("category", "")),
            str(item.get("description", "")),
        ]
    )

    return _preference_matches_text(preference, shopping_text)


def _contains_term(item: dict, term: str) -> bool:
    """Check whether a term matches recommendation information."""
    return _preference_matches_text(
        term,
        _recommendation_text(item),
    )


def _clean_list(values: list) -> list[str]:
    """Remove empty values and duplicates."""
    cleaned = []

    # A list (not a set) is used so the original order is kept.
    for value in values:
        text = _normalise(value)

        if text and text not in cleaned:
            cleaned.append(text)

    return cleaned
