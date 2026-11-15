"""ScheduledStop: one timed stop in a day's schedule (made by DayPlanner)."""

from dataclasses import dataclass

from .itinerary_item import ItineraryItem


@dataclass
class ScheduledStop:
    """One stop in the day's schedule."""
    time: str          # start time, blank for the hotel
    period: str        # Morning, Afternoon, Evening or Overnight
    label: str         # Lunch, Dinner etc, blank for normal places
    item: ItineraryItem
    end: str = ""      # end time, blank for the hotel
    note: str = ""     # warning when the time looks wrong for this place