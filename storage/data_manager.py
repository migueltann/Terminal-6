from models import RecommendationSet
from storage.recommendation_repository import RecommendationRepository


class DataManager:
    """Coordinates recommendation storage and searching.

    The rest of the app talks to DataManager instead of the files directly.
    It passes the work on to a repository (e.g. JsonCsvRepository) and
    turns storage errors into simple results like None or False.
    """

    def __init__(
        self, repository: RecommendationRepository
    ) -> None:
        # The repository is passed in rather than created here, so tests
        # can give DataManager a fake one (dependency injection).
        self.__repository = repository

    def save(self, result: RecommendationSet) -> str:
        """Save a set and return its identifier (the JSON filename)."""
        return self.__repository.save(result)

    def find(self, keyword: str = "") -> list[dict]:
        """Return saved sets whose destination contains the keyword.

        An empty keyword matches everything, so find() lists every set.
        The search ignores upper/lower case.
        """
        keyword = keyword.strip().lower()

        return [
            entry
            for entry in self.__repository.load_all()
            if keyword in str(
                entry.get("destination", "")
            ).lower()
        ]

    def load(
        self, identifier: str
    ) -> RecommendationSet | None:
        """Load a saved set, or return None if it is missing or broken."""
        # OSError covers file problems (e.g. not found); ValueError covers
        # files with bad contents.
        try:
            return self.__repository.load(identifier)
        except (OSError, ValueError):
            return None

    def update(
        self, identifier: str, result: RecommendationSet
    ) -> bool:
        """Replace a saved set; False if it does not exist or cannot be written."""
        try:
            return self.__repository.update(identifier, result)
        except (OSError, ValueError):
            return False

    def rename(self, identifier: str, new_name: str) -> bool:
        """Change the destination name shown for a saved set."""
        new_name = str(new_name).strip()

        if not new_name:
            raise ValueError("The new name cannot be empty.")

        # Load the set, change its name, then save it back.
        result = self.load(identifier)

        if result is None:
            return False

        result.destination = new_name
        return self.update(identifier, result)

    def delete(self, identifier: str) -> bool:
        """Return False if the saved set cannot be deleted."""
        try:
            return self.__repository.delete(identifier)
        except (OSError, ValueError):
            return False
