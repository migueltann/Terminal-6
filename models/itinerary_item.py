"""One place the user added to a day in their itinerary."""

from dataclasses import dataclass
from typing import ClassVar
from .recommendation import Recommendation

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
    best_time: str = "any"      # morning, afternoon, evening or any

    # Allowed meal choices and the longest something can last
    MEALS: ClassVar[tuple[str, ...]] = ("", "lunch", "dinner")
    MAX_DURATION: ClassVar[int] = 24 * 60

    def __post_init__(self) -> None:
        # validate the values when the item is created

        # Same allowed values as Recommendation; unknown becomes "any"
        self.best_time = Recommendation.clean_best_time(self.best_time)

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
            
    @staticmethod
    def _valid_time(text: str) -> bool:
        # checks for HH:MM format, blank is also ok
        if text == "":
            return True

        # Split the time into hours and minutes
        hours, _, minutes = text.partition(":")

        # Both parts must be 2 digits and be a real time
        return (len(hours) == 2 and len(minutes) == 2
                and hours.isdigit() and minutes.isdigit()
                and int(hours) < 24 and int(minutes) < 60)

    def minutes(self) -> int:
        """Start time in minutes from midnight, easier to compare."""
        hours, minutes = self.time.split(":")
        return int(hours) * 60 + int(minutes)

    def to_dict(self) -> dict:
        # Convert the item into a dictionary so it can be saved as JSON
        return {"name": self.name, "type": self.item_type,
                "cost_sgd": self.cost_sgd, "location": self.location,
                "category": self.category, "description": self.description,
                "top_pick": self.top_pick, "meal": self.meal, "time": self.time,
                "duration": self.duration, "best_time": self.best_time}
        
    @classmethod
    def from_dict(cls, data: dict) -> "ItineraryItem":
        # Rebuild the item from the saved dictionary
        # uses blanks for missing fields so older saved itineraries still load
        return cls(name=str(data["name"]), item_type=str(data["type"]),
                   cost_sgd=float(data["cost_sgd"]),
                   location=str(data.get("location") or ""),
                   category=str(data.get("category") or ""),
                   description=str(data.get("description") or ""),
                   top_pick=bool(data.get("top_pick", False)),
                   meal=str(data.get("meal") or ""),
                   time=str(data.get("time") or ""),
                   duration=int(data.get("duration") or 0),
                   best_time=str(data.get("best_time") or "any"))