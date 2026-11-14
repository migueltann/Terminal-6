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

    # ---------- editing ----------

    def add_item(self, day_index: int, item: ItineraryItem) -> None:
        # Add a place to the end of the day
        self.days[day_index].append(item)

    def remove_item(self, day_index: int, position: int) -> ItineraryItem:
        # Remove a place from the day and return it
        return self.days[day_index].pop(position)

    # ---------- building from the builder page ----------

    @classmethod
    def from_selection(cls, recommendation_set: RecommendationSet, source_id: str,
                       daily_budget: float, selection: list[list],
                       title: str = "", start_date: str = "") -> "Itinerary":
        """Builds the itinerary from what the builder page sends.

        Each day is a list of positions in the approved list, either just the
        number or a dict with the meal, time and duration the user picked.
        We get the names and prices from the saved set instead of the browser
        so the user can't change the price by editing the request.
        """
        # Check the plan is a list of days
        if not isinstance(selection, list) or not all(isinstance(day, list) for day in selection):
            raise ValueError("The plan must be a list of days.")

        # Get the approved recommendations the user could pick from
        approved = recommendation_set.approved()
        days = []

        # Go through each day and each place the user picked
        for day in selection:
            items = []
            for entry in day:
                if isinstance(entry, dict) and entry.get("is_custom") is True:
                    name = entry.get("name")
                    item_type = entry.get("type")

                    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
                        raise ValueError(
                            "Personal entry names must be 1 to 100 characters."
                        )

                    if not isinstance(item_type, str) or item_type not in {
                        "activity", "food", "shopping", "accommodation"
                    }:
                        raise ValueError(
                            "Choose a valid category for the personal entry."
                        )

                    items.append(ItineraryItem(
                        name=name.strip(),
                        item_type=item_type,
                        cost_sgd=0,
                        category="Personal entry",
                        description=(
                            "Added by you; cost is not included in budget totals."
                        ),
                        meal=entry.get("meal", ""),
                        time=entry.get("time", ""),
                        duration=entry.get("duration", 0),
                        is_custom=True,
                    ))
                    continue
        
                # Get the position and the user's choices
                if isinstance(entry, dict):
                    position = entry.get("index")
                    meal, time = entry.get("meal", ""), entry.get("time", "")
                    duration = entry.get("duration", 0)
                else:
                    position, meal, time, duration = entry, "", "", 0
                
                # True/False would pass as int so block them too
                if isinstance(position, bool) or not isinstance(position, int) \
                        or not 0 <= position < len(approved):
                    raise ValueError("The plan refers to a recommendation that does not exist.")
                if not isinstance(meal, str):
                    raise ValueError("A meal must be lunch, dinner or left blank.")

                # Copy the details from the saved recommendation
                chosen = approved[position]
                items.append(ItineraryItem(
                    name=chosen.name, item_type=chosen.item_type,
                    cost_sgd=chosen.cost_sgd, location=chosen.location,
                    category=chosen.category, description=chosen.description,
                    top_pick=chosen.is_top_pick(), meal=meal, time=time,
                    duration=duration, best_time=chosen.best_time,
                ))
            days.append(items)

        # Create the itinerary with all the days
        return cls(title=title, destination=recommendation_set.destination,
                   source_id=str(source_id), daily_budget=daily_budget, days=days,
                   start_date=start_date)

    def selection_for(self, recommendation_set: RecommendationSet) -> list[list[dict]]:
        """Opposite of from_selection, used to reopen a saved itinerary in the
        builder. Items that aren't in the set anymore are skipped."""
        # map each recommendation to its position in the list
        positions = {(item.name, item.item_type): index
                     for index, item in enumerate(recommendation_set.approved())}

        # Get the position and the user's choices for every place on every day
        return [[{"index": positions[(item.name, item.item_type)],
                  "meal": item.meal, "time": item.time, "duration": item.duration}
                 for item in day
                 if (item.name, item.item_type) in positions]
                for day in self.days]

    # ---------- saving / loading ----------

    def to_dict(self) -> dict:
        # totals are saved too so the list page can show them
        return {
            "title": self.title,
            "destination": self.destination,
            "source_id": self.source_id,
            "daily_budget": self.daily_budget,
            "start_date": self.start_date,
            "days": [[item.to_dict() for item in day] for day in self.days],
            "trip_total": self.trip_total(),
            "over_budget_days": self.over_budget_days(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Itinerary":
        # Check the saved data is a dictionary
        if not isinstance(data, dict):
            raise TypeError("Saved itinerary must be a dictionary")

        # Rebuild the itinerary from the saved data
        return cls(
            title=str(data.get("title") or ""),
            destination=str(data["destination"]),
            source_id=str(data.get("source_id") or ""),
            daily_budget=float(data["daily_budget"]),
            days=[[ItineraryItem.from_dict(item) for item in day] for day in data["days"]],
            start_date=str(data.get("start_date") or ""),
        )
