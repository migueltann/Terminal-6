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
    note: str = ""     # warning when the time looks wrong for this place


class DayPlanner:
    """Plans out a day and gives each place a start and end time.

    Places the user dragged onto the timeline keep their time and duration.
    Everything else gets slotted into the free gaps automatically, with
    lunch from 12:00 and dinner from 18:30. Hotels always go last.

    Auto times also follow each place's best_time, which the AI gives
    with every recommendation: "morning" places go before lunch,
    "afternoon" places after lunch, "evening" places after dinner, and
    "any" places fill the gaps. A place the user puts at an odd time keeps
    that time but gets a warning note.
    """

    DAY_START = 9 * 60          # auto plan starts at 9am
    LUNCH = 12 * 60
    DINNER = 18 * 60 + 30
    NIGHT_START = 19 * 60       # evening places start from 7pm
    DAY_CLOSE = 18 * 60         # morning / afternoon places should be done by 6pm
    TRAVEL = 30                 # travel time between places (mins)
    DURATION = {"activity": 120, "shopping": 90, "food": 60}   # normal length of each type

    @staticmethod
    def _clock(minutes: int) -> str:
        # convert minutes back to HH:MM, e.g. 570 -> "09:30"
        # "% 24" wraps times past midnight, so 25:00 shows as 01:00
        # ":02d" pads with a zero, so 9 becomes "09"
        return f"{(minutes // 60) % 24:02d}:{minutes % 60:02d}"

    @staticmethod
    def _period(minutes: int) -> str:
        # Work out which part of the day the time is in
        if minutes < 12 * 60:
            return "Morning"
        if minutes < 17 * 60:
            return "Afternoon"
        return "Evening"

    def _note(self, item: ItineraryItem, start: int) -> str:
        """A warning when a place is planned at an unusual time for it."""
        end = start + self._duration(item)
        if item.best_time == "evening" and start < 17 * 60:
            return "Best visited in the evening. Check it is open at this time."
        if item.best_time in ("morning", "afternoon") and end > self.DAY_CLOSE:
            return f"Best visited in the {item.best_time}. It may close before you finish."
        return ""

    def _duration(self, item: ItineraryItem) -> int:
        # user's chosen duration, otherwise the normal one
        return item.duration or self.DURATION.get(item.item_type, 90)

    def _stop(self, start: int, label: str, item: ItineraryItem) -> ScheduledStop:
        # Create one stop with its start and end time
        end = start + self._duration(item)
        return ScheduledStop(self._clock(start), self._period(start), label, item,
                             self._clock(end), self._note(item, start))

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
                # Two time ranges overlap when each one starts before the
                # other one ends.
                if clock < end and clock + length > start:   # overlaps
                    # Move to after the busy time and check again
                    clock = end
                    moved = True
        return clock

    def plan(self, items: list[ItineraryItem]) -> list[ScheduledStop]:
        """Return the day's stops in time order, with the hotel at the end.

        Raises ValueError if two places the user timed themselves overlap.
        """
        # Separate the hotels from everything else
        stays = [item for item in items if item.item_type == "accommodation"]
        others = [item for item in items if item.item_type != "accommodation"]

        # Separate the places the user placed on the timeline from the ones they didn't
        timed = [item for item in others if item.time]
        untimed = [item for item in others if not item.time]

        
        # Check manually timed items for scheduling conflicts.
        timed.sort(key=lambda item: item.minutes())

        # zip(timed, timed[1:]) pairs each item with the one after it,
        # so we can check each item ends before the next one starts.
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
        # (each busy range includes travel time to the next place)
        busy = [(item.minutes(), item.minutes() + self._duration(item) + self.TRAVEL)
                for item in timed]

        # Check if the user already placed a lunch or dinner
        labels = {stop.label for _, stop in timeline}

        # the rest get an automatic time
        meals = [item for item in untimed if item.item_type == "food"]
        visits = [item for item in untimed if item.item_type != "food"]
        lunch, dinner, extras = self._pick_meals(
            meals, "Lunch" in labels, "Dinner" in labels)

        # Use the AI's best_time: morning places before lunch, afternoon
        # places after lunch, evening places after dinner. "any" places
        # fill up the morning first, then the afternoon (user's order kept).
        morning = [item for item in visits if item.best_time == "morning"]
        afternoon = [item for item in visits if item.best_time == "afternoon"]
        evening = [item for item in visits if item.best_time == "evening"]
        anytime = [item for item in visits if item.best_time == "any"]

        # Split the daytime places roughly in half around lunch.
        # half = how many places should go before lunch (rounded up).
        # fill = how many "any" places are needed to top up the morning,
        #        kept between 0 and the number of "any" places.
        # e.g. 1 morning, 1 afternoon, 4 any -> half = 3, fill = 2,
        #      so 3 places go before lunch and 3 after.
        half = (len(morning) + len(afternoon) + len(anytime) + 1) // 2
        fill = max(0, min(len(anytime), half - len(morning)))
        before_lunch = morning + anytime[:fill]
        after_lunch = anytime[fill:] + afternoon

        # Build the order of the day as (item, label) pairs.
        sequence = [(item, "") for item in before_lunch]
        if lunch:
            sequence.append((lunch, "Lunch"))
        sequence += [(item, "") for item in after_lunch]

        if dinner:
            sequence.append((dinner, "Dinner"))
        sequence += [(item, "Evening") for item in evening]
        sequence += [(item, "Extra meal") for item in extras]

        # Start the day at 9am and go through each place in order
        clock = self.DAY_START
        for item, label in sequence:
            # Make sure lunch and dinner aren't too early
            if label == "Lunch":
                clock = max(clock, self.LUNCH)
            elif label == "Dinner":
                clock = max(clock, self.DINNER)
            elif label == "Evening":
                clock = max(clock, self.NIGHT_START)

            # Find a free time for this place and add it to the timeline
            length = self._duration(item) + self.TRAVEL
            clock = self._next_free(clock, length, busy)
            # "Evening" is only used for ordering, so the stop gets no label
            shown = "" if label == "Evening" else label
            timeline.append((clock, self._stop(clock, shown, item)))

            # Move the clock forward to after this place
            clock += length

        # sort by time and add the hotel at the end
        timeline.sort(key=lambda entry: entry[0])
        stops = [stop for _, stop in timeline]
        stops += [ScheduledStop("", "Overnight", "Stay", item) for item in stays]
        return stops
