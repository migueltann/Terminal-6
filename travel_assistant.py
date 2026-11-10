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