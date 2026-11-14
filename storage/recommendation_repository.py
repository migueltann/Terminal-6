"""Defines the operations required for recommendation storage."""

from abc import ABC, abstractmethod
from models import RecommendationSet

class RecommendationRepository(ABC):
    """Interface for recommendation storage.

    It only lists the methods every storage class must have; it does not
    say how they work. JsonCsvRepository is the real version that uses
    files. Because DataManager only relies on these methods, the storage
    could be swapped (e.g. for a database) without changing DataManager.
    """

    @abstractmethod
    def save(self, result: RecommendationSet) -> str:
        """Save a recommendation set and return its identifier."""
        pass

    @abstractmethod
    def load(self, identifier: str) -> RecommendationSet:
        """Load a recommendation set or raise an error."""
        pass

    @abstractmethod
    def load_all(self) -> list[dict]:
        """Return index metadata for all saved recommendation sets."""
        pass

    @abstractmethod
    def update(self, identifier: str, result: RecommendationSet) -> bool:
        """Replace a saved set; return False if its identifier is unknown."""
        pass

    @abstractmethod
    def delete(self, identifier: str) -> bool:
        """Delete a saved set; return False if its identifier is unknown."""
        pass