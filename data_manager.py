"""Saves processed recommendation results to JSON and CSV files."""
#Set up data storage directory and index file
import csv
import json
import os
from datetime import datetime

DATA_DIR = "data"
INDEX_FILE = os.path.join(DATA_DIR, "recommendation_sets.json")


def ensure_storage_directory():
    """Create the data folder and index file if they do not exist yet."""

    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "w", encoding="utf-8") as file:
            json.dump([], file, indent=4)


def _safe_name(value):
    """Create a simple file-safe name from the destination."""

    return "".join(
        character.lower() if character.isalnum() else "_"
        for character in value
    ).strip("_")

