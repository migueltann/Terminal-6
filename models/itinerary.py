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

    def __post_init__(self) -> None:
        # use the destination if no title was given
        self.title = str(self.title).strip() or str(self.destination).strip()
        if not self.title:
            raise ValueError("An itinerary needs a title or destination.")

        # Check the title is not too long
        if len(self.title) > 100:
            raise ValueError("The itinerary title must be 100 characters or fewer.")

        # Check the budget is a valid number within the limit
        budget = float(self.daily_budget)
        if not math.isfinite(budget) or budget < 0 or budget > self.MAX_BUDGET:
            raise ValueError(f"Daily budget must be between 0 and {self.MAX_BUDGET:,.0f}.")
        self.daily_budget = budget

        # Check the number of days
        if not 1 <= len(self.days) <= self.MAX_DAYS:
            raise ValueError(f"An itinerary must have between 1 and {self.MAX_DAYS} days.")

        # Check no day has too many places
        if any(len(day) > self.MAX_ITEMS_PER_DAY for day in self.days):
            raise ValueError(f"A day can hold at most {self.MAX_ITEMS_PER_DAY} items.")

        # make sure the start date is a real date
        self.start_date = str(self.start_date or "").strip()
        if self.start_date:
            try:
                self.start_date = date.fromisoformat(self.start_date).isoformat()
            except ValueError as exc:
                raise ValueError("The start date must be a valid date.") from exc

    # ---------- dates and schedule ----------

    def date_for(self, day_index: int) -> Optional[date]:
        """Date of the day (day_index starts at 0). None if there's no start date."""
        if not self.start_date:
            return None
        # Add the number of days to the start date
        return date.fromisoformat(self.start_date) + timedelta(days=day_index)

    def schedule(self, day_index: int) -> list[ScheduledStop]:
        """The day's stops with their times."""
        return DayPlanner().plan(self.days[day_index])

    # ---------- budget ----------

    def day_total(self, day_index: int) -> float:
        # Add up the cost of everything on the day
        return sum(item.cost_sgd for item in self.days[day_index])

    def trip_total(self) -> float:
        # Add up the cost of every day
        return sum(self.day_total(index) for index in range(len(self.days)))

    def trip_budget(self) -> float:
        # Budget for the whole trip
        return self.daily_budget * len(self.days)

    def is_over_budget(self, day_index: int) -> bool:
        # Check if the day costs more than the daily budget
        return self.day_total(day_index) > self.daily_budget

    def over_budget_days(self) -> list[int]:
        """Day numbers that are over budget (starting from 1)."""
        return [index + 1 for index in range(len(self.days)) if self.is_over_budget(index)]

    def item_count(self) -> int:
        # Count how many places are in the whole trip
        return sum(len(day) for day in self.days)
