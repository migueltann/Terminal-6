"""Works out the schedule (times) for one day."""

from dataclasses import dataclass
from typing import Optional

from .itinerary_item import ItineraryItem


@dataclass
class ScheduledStop:
    """One stop in the day's schedule."""
    time: str          # start time, blank for the hotel
    period: str        # Morning, Afternoon, Evening or Overnight
    label: str         # Lunch, Dinner etc, blank for normal places
    item: ItineraryItem
    end: str = ""      # end time, blank for the hotel


class DayPlanner:
    """Plans out a day and gives each place a start and end time.

    Places the user dragged onto the timeline keep their time and duration.
    Everything else gets slotted into the free gaps automatically, with
    lunch from 12:00 and dinner from 18:30. Hotels always go last.
    """

    DAY_START = 9 * 60          # auto plan starts at 9am
    LUNCH = 12 * 60
    DINNER = 18 * 60 + 30
    TRAVEL = 30                 # travel time between places (mins)
    DURATION = {"activity": 120, "shopping": 90, "food": 60}   # normal length of each type
