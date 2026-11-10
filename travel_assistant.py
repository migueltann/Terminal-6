
from typing import Optional

from ai.ai_manager import AIManager
from filtering.logic_manager import LogicManager
from data_manager import DataManager
from storage.json_csv_repository import JsonCsvRepository
from models import Recommendation, RecommendationSet, UserRequirements


class TravelAssistant:
    """Coordinate AI generation, filtering and storage."""

    def __init__(
        self,
        ai_manager: Optional[AIManager] = None,
        logic_manager: Optional[LogicManager] = None,
        data_manager: Optional[DataManager] = None,
    ):
        self._ai_manager = (
            ai_manager if ai_manager is not None else AIManager()
        )

        self._logic_manager = (
            logic_manager if logic_manager is not None else LogicManager()
        )

        self._data_manager = (
            data_manager if data_manager is not None
            else DataManager(JsonCsvRepository())
        )

    def generate_trip(
        self,
        requirements: UserRequirements,
        notify=None,
        save: bool = False,
    ) -> RecommendationSet:
        """Generate, filter and optionally save recommendations."""

        if not isinstance(requirements, UserRequirements):
            raise TypeError(
                "requirements must be a UserRequirements object"
            )

        # Step 1: Generate recommendations.
        raw_items = self._ai_manager.generate_recommendations(
            destination=requirements.destination,
            user_inputs=requirements.to_dict(),
            notify=notify,
        )

        # Step 2: Convert dictionaries to objects.
        recommendations = [
            Recommendation.from_dict(item)
            for item in raw_items
        ]

        # Step 3: Filter recommendations.
        result = self._logic_manager.process(
            requirements,
            recommendations,
        )

        # Step 4: Save the result if requested.
        if save:
            self._data_manager.save(result)

        return result
