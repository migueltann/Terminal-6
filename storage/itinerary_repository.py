"""Itinerary storage. ItineraryRepository is the interface and
JsonItineraryRepository saves everything into data/itineraries.json."""

import json
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from models import Itinerary


def _now() -> str:
    # Get the current date and time as text
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _summary(identifier: str, data: dict) -> dict:
    """Only the fields needed for the itinerary list page."""
    return {
        "id": identifier,
        "title": data.get("title", ""),
        "destination": data.get("destination", ""),
        "source_id": data.get("source_id", ""),
        "day_count": len(data.get("days", [])),
        "item_count": sum(len(day) for day in data.get("days", [])),
        "daily_budget": data.get("daily_budget", 0),
        "trip_total": data.get("trip_total", 0),
        "over_budget_days": data.get("over_budget_days", []),
        "saved_at": data.get("saved_at", ""),
        "updated_at": data.get("updated_at", ""),
    }


class ItineraryRepository(ABC):
    """Interface for itinerary storage (CRUD). Any storage class has to
    implement these methods."""

    @abstractmethod
    def save(self, itinerary: Itinerary) -> str:
        """Create: saves a new itinerary and returns its id."""

    @abstractmethod
    def load(self, identifier: str) -> Itinerary:
        """Read: returns one itinerary, raises FileNotFoundError if not found."""

    @abstractmethod
    def load_all(self) -> list[dict]:
        """Read: summaries of all itineraries, oldest first."""

    @abstractmethod
    def update(self, identifier: str, itinerary: Itinerary) -> bool:
        """Update: replaces an itinerary, False if the id doesn't exist."""

    @abstractmethod
    def delete(self, identifier: str) -> bool:
        """Delete: removes an itinerary, False if the id doesn't exist."""


class JsonItineraryRepository(ItineraryRepository):
    """Saves all itineraries in one JSON file as a list."""

    def __init__(self, data_dir: str = "data") -> None:
        # Set up the folder and the file path
        self.__data_dir = data_dir
        self.__path = os.path.join(data_dir, "itineraries.json")

    def _read(self) -> list[dict]:
        # Read all the itineraries from the file
        try:
            with open(self.__path, "r", encoding="utf-8") as file:
                entries = json.load(file)
        except FileNotFoundError:
            return []           # nothing saved yet
        except json.JSONDecodeError as exc:
            raise ValueError("The itineraries file is damaged.") from exc
        return entries if isinstance(entries, list) else []

    def _write(self, entries: list[dict]) -> None:
        # Create the folder if it doesn't exist
        os.makedirs(self.__data_dir, exist_ok=True)

        # Save all the itineraries back into the file
        with open(self.__path, "w", encoding="utf-8") as file:
            json.dump(entries, file, indent=4, ensure_ascii=False)

    @staticmethod
    def _find(entries: list[dict], identifier: str) -> Optional[dict]:
        # Find the itinerary with this id, None if it's not there
        return next((entry for entry in entries if entry.get("id") == identifier), None)
