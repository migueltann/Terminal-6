"""Stores recommendation sets using JSON and CSV files."""

import csv
import json
import os

from .recommendation_repository import RecommendationRepository
from models import RecommendationSet


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

    def load_all(self) -> list[dict]:
        """Return metadata for all saved recommendation sets."""
        return [
            {
                **entry,
                "filename": os.path.basename(
                    entry.get("json_path", "")
                ),
            }
            for entry in self._read_index()
        ]

    def load(self, identifier: str) -> RecommendationSet:
        """Load a recommendation set using its JSON filename."""
        entry = next(
            (
                entry
                for entry in self.load_all()
                if entry["filename"] == identifier
            ),
            None,
        )

        if entry is None:
            raise FileNotFoundError(
                f"Saved recommendation set not found: {identifier}"
            )

        with open(
            entry["json_path"], "r", encoding="utf-8"
        ) as file:
            data = json.load(file)

        try:
            return RecommendationSet.from_dict(data)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "The saved recommendation set has an invalid structure."
            ) from exc

    def delete(self, identifier: str) -> bool:
        """Delete a saved recommendation set using its JSON filename."""
        entries = self._read_index()

        entry = next(
            (
                entry
                for entry in entries
                if os.path.basename(
                    entry.get("json_path", "")
                ) == identifier
            ),
            None,
        )

        if entry is None:
            return False

        for path_key in ("json_path", "csv_path"):
            path = entry.get(path_key)

            if path:
                try:
                    os.remove(path)
                except FileNotFoundError:
                    pass

        entries.remove(entry)
        self._write_index(entries)

        return True

def _write_csv(
    self, result: RecommendationSet, path: str
) -> None:
    """Write approved recommendations to a CSV file."""
    fieldnames = [
        "type",
        "name",
        "category",
        "estimated_cost_sgd",
        "location",
        "environment",
        "description",
        "tags",
        "transport_options",
        "dietary_tags",
        "eligible",
        "passed_rules",
        "failed_rules",
    ]

    list_fields = (
            "tags",
            "transport_options",
            "dietary_tags",
            "passed_rules",
            "failed_rules",
    )

    with open(
            path, "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=fieldnames
        )
        writer.writeheader()