
"""Shared helper functions for recommendation filtering."""

import re
from difflib import SequenceMatcher
from typing import Any


CHEAPEST_TOP_PICK_COUNT = 3


def _normalise(value: Any) -> str:
    """Convert text to lowercase and remove unnecessary symbols."""
    value = str(value or "").strip().lower()
    value = re.sub(r"[_\-]+", " ", value)
    value = re.sub(r"[^\w\s]", " ", value)
    return " ".join(value.split())


def _active_preferences(values: Any) -> list[str]:
    """Remove empty answers and placeholder preferences."""
    if not isinstance(values, list):
        return []

    return [
        str(value).strip()
        for value in values
        if _normalise(value) not in {"", "any", "none"}
    ]


def _as_text_list(value: Any) -> list[str]:
    """Convert a list into non-empty strings."""
    if not isinstance(value, list):
        return []

    return [
        str(item).strip()
        for item in value
        if str(item).strip()
    ]


def _recommendation_text(item: dict) -> str:
    """Combine searchable recommendation information."""
    fields = [
        item.get("name", ""),
        item.get("category", ""),
        item.get("description", ""),
        item.get("location", ""),
    ]

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

    return _normalise(" ".join(str(field) for field in fields))


def _preference_matches_text(preference: str, text: str) -> bool:
    """Check exact, word-based and approximate preference matches."""
    pref = _normalise(preference)
    searchable = _normalise(text)

    if not pref or not searchable:
        return False

    pref_words = pref.split()
    text_words = searchable.split()

    if " " + pref + " " in " " + searchable + " ":
        return True

    if set(pref_words).issubset(text_words):
        return True

    if len(pref) >= 5:
        size = len(pref_words)

        for start in range(len(text_words) - size + 1):
            candidate = " ".join(text_words[start:start + size])

            if SequenceMatcher(None, pref, candidate).ratio() >= 0.88:
                return True

    return False


def matches_shopping_preference(item: dict, preference: str) -> bool:
    """Match shopping preferences against recommendation information."""
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

    for value in values:
        text = _normalise(value)

        if text and text not in cleaned:
            cleaned.append(text)

    return cleaned
