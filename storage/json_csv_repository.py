"""Stores recommendation sets using JSON and CSV files.

Files in the data folder:
- recommendation_sets.json: the "index", a list of every saved set with
  its destination, item count, file paths and when it was saved.
- <destination>_<timestamp>.json: the full saved set (used to load it again).
- <destination>_<timestamp>.csv: the approved items as a spreadsheet.
"""

import csv
import json
import os
import tempfile

from .recommendation_repository import RecommendationRepository
from models import RecommendationSet
from datetime import datetime

class JsonCsvRepository(RecommendationRepository):
    """File-based implementation of recommendation storage."""

    def __init__(self, data_dir: str = "data"):
        # Tests pass in a temporary folder here so real data is not touched.
        self.__data_dir = data_dir
        self.__index_file = os.path.join(
            data_dir,
            "recommendation_sets.json",
        )

    def _ensure_storage_directory(self) -> None:
        """Create the storage directory if needed."""
        # exist_ok=True: no error if the folder is already there.
        os.makedirs(self.__data_dir, exist_ok=True)

    
    def _read_index(self) -> list[dict]:
        """Read saved-set metadata from the index."""
        try:
            with open(
                self.__index_file, "r", encoding="utf-8"
            ) as file:
                entries = json.load(file)

        # No index yet means nothing has been saved, which is not an error.
        except FileNotFoundError:
            return []

        # The file exists but is not valid JSON (e.g. edited by hand).
        # "from exc" keeps the original error attached for debugging.
        except json.JSONDecodeError as exc:
            raise ValueError(
                "The storage index contains invalid JSON."
            ) from exc

        # Valid JSON, but not the shape we expect (a list of dicts).
        if not isinstance(entries, list) or not all(
            isinstance(entry, dict) for entry in entries
        ):
            raise ValueError(
                "The storage index must contain a list of dictionaries."
            )

        return entries


    def _write_index(self, entries: list[dict]) -> None:
        """Replace the index only after writing its new contents successfully."""
        # Writing straight into the index could leave it half-written (and
        # every saved set lost) if the app crashed mid-write. Instead, write
        # a temporary file first, then swap it in with os.replace(), which
        # happens in one step: the index is either the old or the new one.
        self._ensure_storage_directory()
        temporary_path = None

        try:
            # delete=False keeps the temp file after closing it, so it can
            # be moved into place below.
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.__data_dir,
                prefix=".recommendation_sets_",
                suffix=".tmp",
                delete=False,
            ) as file:
                temporary_path = file.name
                json.dump(
                    entries,
                    file,
                    indent=4,               # pretty-print for easy reading
                    ensure_ascii=False,     # keep characters like é or 中
                    allow_nan=False,        # NaN is not valid JSON, so refuse it
                )

            os.replace(temporary_path, self.__index_file)

        # Runs whether the write worked or failed. After a successful
        # replace the temp file is already gone (FileNotFoundError, ignored);
        # after a failure, this deletes the leftover temp file.
        finally:
            if temporary_path is not None:
                try:
                    os.remove(temporary_path)
                except FileNotFoundError:
                    pass

    @staticmethod
    def _safe_name(value: str) -> str:
        """Convert a destination into a filename component."""
        # Keep letters and digits, replace everything else with "_",
        # e.g. "Kuala Lumpur!" -> "kuala_lumpur". Falls back to "trip"
        # if nothing usable is left.
        name = "".join(
            character.lower() if character.isalnum() else "_"
            for character in value
        ).strip("_")

        return name or "trip"

    def load_all(self) -> list[dict]:
        """Return metadata for all saved recommendation sets."""
        # Copy each index entry and add a "filename" key (just the file
        # name, without the folder). The filename is the set's identifier
        # used by load(), update() and delete().
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
        # next() returns the first matching entry, or None if none match.
        # Only files listed in the index can be loaded, so a made-up
        # filename such as "../secret.json" is never opened.
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

        try:
            with open(
                entry["json_path"], "r", encoding="utf-8"
            ) as file:
                data = json.load(file)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "The saved recommendation file contains invalid JSON."
            ) from exc

        # Turn the dict back into objects. Missing keys or wrong types
        # mean the file's structure is wrong.
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

        # Delete both data files. A file that is already missing is fine.
        for path_key in ("json_path", "csv_path"):
            path = entry.get(path_key)

            if path:
                try:
                    os.remove(path)
                except FileNotFoundError:
                    pass

        # Remove the set from the index and save the index.
        entries.remove(entry)
        self._write_index(entries)

        return True

    def update(
        self, identifier: str, result: RecommendationSet
    ) -> bool:
        """Overwrite a saved set's JSON/CSV files and refresh its index entry."""
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

        # "w" overwrites the existing file with the updated set.
        with open(
            entry["json_path"], "w", encoding="utf-8"
        ) as file:
            json.dump(
                result.to_dict(),
                file,
                indent=4,
                ensure_ascii=False,
            )

        self._write_csv(result, entry["csv_path"])

        # Keep the index in step, e.g. after the set was renamed.
        # entry is the same dict object that sits inside entries, so
        # changing it here changes the list that gets written.
        entry["destination"] = result.destination
        entry["approved_count"] = len(result.approved())
        self._write_index(entries)

        return True

    def _write_csv(
        self, result: RecommendationSet, path: str
    ) -> None:
        """Write approved recommendations to a CSV file."""
        # The CSV columns, in order.
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

        # Columns that hold lists. A CSV cell can only hold text, so these
        # are joined into one string: ["a", "b"] -> "a, b".
        list_fields = (
                "tags",
                "transport_options",
                "dietary_tags",
                "passed_rules",
                "failed_rules",
        )

        # newline="" stops Windows adding blank lines between CSV rows.
        with open(
                path, "w", newline="", encoding="utf-8"
        ) as file:
            # DictWriter writes each row from a dict, using fieldnames
            # as the column order.
            writer = csv.DictWriter(
                file, fieldnames=fieldnames
            )
            writer.writeheader()

            for item in result.approved():
                    item_data = item.to_dict()

                    row = {
                        field: item_data.get(field, "")
                        for field in fieldnames
                    }

                    for field in list_fields:
                        row[field] = ", ".join(
                            item_data.get(field, [])
                        )

                    writer.writerow(row)


    def save(self, result: RecommendationSet) -> str:
        """Save JSON and CSV files and return the JSON filename."""
        entries = self._read_index()
        self._ensure_storage_directory()

        # Name the files after the destination and the current time down
        # to the microsecond (%f), e.g. "japan_20261113_165806_645803",
        # so two saves never get the same name.
        timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
        )
        destination_name = self._safe_name(
            result.destination
        )
        base_name = f"{destination_name}_{timestamp}"

        json_path = os.path.join(
            self.__data_dir, base_name + ".json"
        )
        csv_path = os.path.join(
            self.__data_dir, base_name + ".csv"
        )

        # "x" = create a new file, and fail if it already exists, so an
        # existing save can never be overwritten by accident.
        with open(
            json_path, "x", encoding="utf-8"
        ) as file:
            json.dump(
                result.to_dict(),
                file,
                indent=4,
                ensure_ascii=False,
            )

        self._write_csv(result, csv_path)

        # Add the new set to the index so it shows up in the saved list.
        entries.append(
            {
                "destination": result.destination,
                "approved_count": len(result.approved()),
                "json_path": json_path,
                "csv_path": csv_path,
                "saved_at": timestamp,
            }
        )

        self._write_index(entries)

        return os.path.basename(json_path)