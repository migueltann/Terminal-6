"""One place the user added to a day in their itinerary."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass
class ItineraryItem:
    """Stores a copy of the recommendation's details so the itinerary
    still shows the right info even if the saved set changes later."""
    name: str
    item_type: str              # activity, food, shopping or accommodation
    cost_sgd: float
    location: str = ""
    category: str = ""
    description: str = ""
    top_pick: bool = False
    meal: str = ""              # only for food, lunch or dinner (blank means auto)
    time: str = ""              # start time on the timeline, blank if not placed yet
    duration: int = 0           # in minutes, 0 means use the normal length

    # Allowed meal choices and the longest something can last
    MEALS: ClassVar[tuple[str, ...]] = ("", "lunch", "dinner")
    MAX_DURATION: ClassVar[int] = 24 * 60

    def __post_init__(self) -> None:
        # validate the values when the item is created

        # Check the meal is one of the allowed choices
        if self.meal not in self.MEALS:
            raise ValueError("A meal must be lunch, dinner or left blank.")
        if self.item_type != "food":
            self.meal = ""      # only food can be a meal

        # Check the time is in the right format
        if not isinstance(self.time, str) or not self._valid_time(self.time):
            raise ValueError("A time must look like 09:00, or be left blank.")

        # Check the duration is a whole number between 0 and 24 hours
        # True/False would pass as int so block them too
        if isinstance(self.duration, bool) or not isinstance(self.duration, int) \
                or not 0 <= self.duration <= self.MAX_DURATION:
            raise ValueError("A duration must be between 0 and 24 hours.")

        # hotels are just the overnight stay so they don't get a time
        if self.item_type == "accommodation":
            self.time = ""
            self.duration = 0 