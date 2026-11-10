from typing import Optional

from ai.ai_manager import AIManager
from filtering.logic_manager import LogicManager
from models import Recommendation, RecommendationSet, UserRequirements


class TravelAssistant:
    """Coordinate AI generation and recommendation filtering."""

    def __init__(
        self,
        ai_manager: Optional[AIManager] = None,
        logic_manager: Optional[LogicManager] = None,
    ):
        self._ai_manager = (
            ai_manager if ai_manager is not None else AIManager()
        )
        self._logic_manager = (
            logic_manager if logic_manager is not None else LogicManager()
        )

    def generate_trip(
        self,
        requirements: UserRequirements,
        notify=None,
    ) -> RecommendationSet:
        """Generate, convert and filter travel recommendations."""

        if not isinstance(requirements, UserRequirements):
            raise TypeError(
                "requirements must be a UserRequirements object"
            )

        # Step 1: Generate recommendations using Gemini.
        raw_items = self._ai_manager.generate_recommendations(
            destination=requirements.destination,
            user_inputs=requirements.to_dict(),
            notify=notify,
        )

        # Step 2: Convert dictionaries into OOP model objects.
        recommendations = [
            Recommendation.from_dict(item)
            for item in raw_items
        ]

        # Step 3: Apply filtering rules.
        result = self._logic_manager.process(
            requirements,
            recommendations,
        )

        return result
