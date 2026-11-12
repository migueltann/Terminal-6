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
