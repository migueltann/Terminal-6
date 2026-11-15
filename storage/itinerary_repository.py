"""ItineraryRepository: the interface (CRUD contract) for itinerary storage."""

from abc import ABC, abstractmethod

from models import Itinerary


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