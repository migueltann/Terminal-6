"""Stores recommendation sets using JSON and CSV files."""

import json
import os

from .recommendation_repository import RecommendationRepository


class JsonCsvRepository(RecommendationRepository):
    """File-based implementation of recommendation storage."""

    def __init__(self, data_dir: str = "data"):
        self._data_dir = data_dir
        self._index_file = os.path.join(
            data_dir,
            "recommendation_sets.json",
        )

    def _ensure_storage_directory(self) -> None:
        """Create the storage directory if needed."""
        os.makedirs(self._data_dir, exist_ok=True)

    def _read_index(self) -> list[dict]:
        """Read saved-set metadata from the index."""
        try:
            with open(
                self._index_file, "r", encoding="utf-8"
            ) as file:
                entries = json.load(file)
        except FileNotFoundError:
            return []

        if not isinstance(entries, list) or not all(
            isinstance(entry, dict) for entry in entries
        ):
            raise ValueError(
                "The storage index must contain a list of dictionaries."
            )

        return entries

    def _write_index(self, entries: list[dict]) -> None:
        """Write saved-set metadata to the index."""
        self._ensure_storage_directory()

        with open(
            self._index_file, "w", encoding="utf-8"
        ) as file:
            json.dump(entries, file, indent=4)

    @staticmethod
    def _safe_name(value: str) -> str:
        """Convert a destination into a filename component."""
        name = "".join(
            character.lower() if character.isalnum() else "_"
            for character in value
        ).strip("_")

        return name or "trip"