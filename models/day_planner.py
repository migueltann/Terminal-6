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

    @staticmethod
    def _clock(minutes: int) -> str:
        # convert minutes back to HH:MM
        return f"{(minutes // 60) % 24:02d}:{minutes % 60:02d}"

    @staticmethod
    def _period(minutes: int) -> str:
        # Work out which part of the day the time is in
        if minutes < 12 * 60:
            return "Morning"
        if minutes < 17 * 60:
            return "Afternoon"
        return "Evening"

    def _duration(self, item: ItineraryItem) -> int:
        # user's chosen duration, otherwise the normal one
        return item.duration or self.DURATION.get(item.item_type, 90)

    def _stop(self, start: int, label: str, item: ItineraryItem) -> ScheduledStop:
        # Create one stop with its start and end time
        end = start + self._duration(item)
        return ScheduledStop(self._clock(start), self._period(start), label, item,
                             self._clock(end))

    @staticmethod
    def _timed_label(item: ItineraryItem) -> str:
        """Label for food the user placed themselves."""
        # Only food gets a meal label
        if item.item_type != "food":
            return ""

        # Use the meal the user picked if there is one
        if item.meal:
            return item.meal.title()

        # no meal chosen so go by the time
        hour = item.minutes() // 60
        if hour < 11:
            return "Breakfast"
        return "Lunch" if hour < 16 else "Dinner"

    @staticmethod
    def _pick_meals(meals: list[ItineraryItem], lunch_taken: bool, dinner_taken: bool):
        """Decides which unplaced food is lunch, dinner or an extra meal."""
        # Separate the food based on what the user picked in the dropdown
        lunches = [item for item in meals if item.meal == "lunch"]
        dinners = [item for item in meals if item.meal == "dinner"]
        auto = [item for item in meals if item.meal == ""]

        # auto ones fill lunch first then dinner (unless the user already placed one)
        if not lunches and auto and not lunch_taken:
            lunches.append(auto.pop(0))
        if not dinners and auto and not dinner_taken:
            dinners.append(auto.pop(0))

        # Take the first lunch and dinner, the rest become extra meals
        lunch: Optional[ItineraryItem] = lunches[0] if lunches else None
        dinner: Optional[ItineraryItem] = dinners[0] if dinners else None
        extras = lunches[1:] + dinners[1:] + auto
        return lunch, dinner, extras

    def _next_free(self, clock: int, length: int, busy: list[tuple[int, int]]) -> int:
        """Finds the next time that doesn't clash with the user's placed items."""
        # Keep checking until the time doesn't overlap anything
        moved = True
        while moved:
            moved = False
            for start, end in busy:
                if clock < end and clock + length > start:   # overlaps
                    # Move to after the busy time and check again
                    clock = end
                    moved = True
        return clock

    def plan(self, items: list[ItineraryItem]) -> list[ScheduledStop]:
        # Separate the hotels from everything else
        stays = [item for item in items if item.item_type == "accommodation"]
        others = [item for item in items if item.item_type != "accommodation"]

        # Separate the places the user placed on the timeline from the ones they didn't
        timed = [item for item in others if item.time]
        untimed = [item for item in others if not item.time]

        
        # Check manually timed items for scheduling conflicts.
        timed.sort(key=lambda item: item.minutes())

        for previous, current in zip(timed, timed[1:]):
            previous_end = previous.minutes() + self._duration(previous)

            if current.minutes() < previous_end:
                raise ValueError(
                    f"Scheduling conflict: {previous.name} and "
                    f"{current.name} have overlapping times."
                )

        # Manually placed items keep their chosen times.
        timeline = [
            (
                item.minutes(),
                self._stop(item.minutes(), self._timed_label(item), item)
            )
            for item in timed
        ]


        # Keep track of which times are already taken
        busy = [(item.minutes(), item.minutes() + self._duration(item) + self.TRAVEL)
                for item in timed]

        # Check if the user already placed a lunch or dinner
        labels = {stop.label for _, stop in timeline}

        # the rest get an automatic time
        meals = [item for item in untimed if item.item_type == "food"]
        visits = [item for item in untimed if item.item_type != "food"]
        lunch, dinner, extras = self._pick_meals(
            meals, "Lunch" in labels, "Dinner" in labels)

        # half the visits before lunch, the rest after, then dinner
        half = (len(visits) + 1) // 2
        sequence = [(item, "") for item in visits[:half]]
        if lunch:
            sequence.append((lunch, "Lunch"))
        sequence += [(item, "") for item in visits[half:]]
        if dinner:
            sequence.append((dinner, "Dinner"))
        sequence += [(item, "Extra meal") for item in extras]

        # Start the day at 9am and go through each place in order
        clock = self.DAY_START
        for item, label in sequence:
            # Make sure lunch and dinner aren't too early
            if label == "Lunch":
                clock = max(clock, self.LUNCH)
            elif label == "Dinner":
                clock = max(clock, self.DINNER)

            # Find a free time for this place and add it to the timeline
            length = self._duration(item) + self.TRAVEL
            clock = self._next_free(clock, length, busy)
            timeline.append((clock, self._stop(clock, label, item)))

            # Move the clock forward to after this place
            clock += length

        # sort by time and add the hotel at the end
        timeline.sort(key=lambda entry: entry[0])
        stops = [stop for _, stop in timeline]
        stops += [ScheduledStop("", "Overnight", "Stay", item) for item in stays]
        return stops
