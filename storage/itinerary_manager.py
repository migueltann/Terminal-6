"""Handles itinerary storage, same idea as DataManager for recommendation sets."""

from typing import Optional

from models import Itinerary, RecommendationSet
from .itinerary_repository import ItineraryRepository


class ItineraryManager:
    """Builds, saves, finds, updates and deletes itineraries.
    The actual storage is done by the repository passed in."""

    def __init__(self, repository: ItineraryRepository) -> None:
        # Keep the repository private
        self.__repository = repository

    @staticmethod
    def build(recommendation_set: RecommendationSet, source_id: str,
              daily_budget: float, selection: list[list[int]],
              title: str = "", start_date: str = "") -> Itinerary:
        """Makes an Itinerary from what the user picked in the builder."""
        return Itinerary.from_selection(recommendation_set, source_id,
                                        daily_budget, selection, title, start_date)

    def save(self, itinerary: Itinerary) -> str:
        """Create. File errors are passed on so the web app can show a message."""
        return self.__repository.save(itinerary)

    def find(self, keyword: str = "") -> list[dict]:
        """Read. Searches by title or destination (blank keyword returns all)."""
        # Remove extra spaces and ignore upper/lower case
        keyword = str(keyword).strip().lower()

        # Keep the itineraries where the title or destination matches
        return [
            entry for entry in self.__repository.load_all()
            if keyword in str(entry.get("title", "")).lower()
            or keyword in str(entry.get("destination", "")).lower()
        ]

    def load(self, identifier: str) -> Optional[Itinerary]:
        """Read one itinerary, returns None if it's missing or can't be read."""
        try:
            return self.__repository.load(identifier)
        except (OSError, ValueError):
            return None

    def update(self, identifier: str, itinerary: Itinerary) -> bool:
        """Update. Returns False if not found or the file can't be written."""
        try:
            return self.__repository.update(identifier, itinerary)
        except (OSError, ValueError):
            return False

    def delete(self, identifier: str) -> bool:
        """Delete. Returns False if not found or the file can't be written."""
        try:
            return self.__repository.delete(identifier)
        except (OSError, ValueError):
            return False
