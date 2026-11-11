"""A day-by-day trip plan built from saved recommendations."""

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import ClassVar, Optional

from .day_planner import DayPlanner, ScheduledStop
from .itinerary_item import ItineraryItem
from .recommendation_set import RecommendationSet


@dataclass
class Itinerary:
    """The trip plan. days is a list of days, each day is a list of items."""
    title: str
    destination: str
    source_id: str              # id of the saved recommendation set it came from
    daily_budget: float
    days: list[list[ItineraryItem]] = field(default_factory=lambda: [[]])
    start_date: str = ""        # optional, YYYY-MM-DD

    # Limits for the itinerary
    MAX_DAYS: ClassVar[int] = 14
    MAX_ITEMS_PER_DAY: ClassVar[int] = 30
    MAX_BUDGET: ClassVar[float] = 100_000
