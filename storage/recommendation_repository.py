""""defines the operations required for recommendation storage"""

from abc import ABC, abstractmethod
from models import RecommendationSet

class RecommendationRepository(ABC):
    """Interface for recommendation storage."""

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