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
