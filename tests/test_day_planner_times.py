"""Auto-planned times follow the AI's best_time (no zoo at night)."""
import pytest

from ai.prompt_builder import PromptBuilder
from models import DayPlanner, ItineraryItem, Recommendation


def place(name, best_time="any", item_type="activity", time=""):
    return ItineraryItem(name, item_type, 10, best_time=best_time, time=time)


NIGHT_SAFARI = place("Night Safari", "evening")
ZOO = place("Singapore Zoo", "morning")


def test_the_bug_from_the_screenshot_is_fixed():
    # Night Safari added first and the zoo last used to give
    # Night Safari 09:00 and the zoo 17:30.
    stops = DayPlanner().plan([NIGHT_SAFARI, place("Gardens by the Bay"),
                               place("Singapore Flyer"), ZOO])
    times = {stop.item.name: stop.time for stop in stops}

    assert times["Singapore Zoo"] == "09:00"     # morning place goes first
    assert times["Night Safari"] >= "19:00"
    assert all(stop.note == "" for stop in stops)


def test_evening_place_goes_after_dinner():
    stops = DayPlanner().plan([NIGHT_SAFARI, place("Hawker", item_type="food"),
                               place("Restaurant", item_type="food")])

    assert [(stop.time, stop.label, stop.item.name) for stop in stops] == [
        ("12:00", "Lunch", "Hawker"),
        ("18:30", "Dinner", "Restaurant"),
        ("20:00", "", "Night Safari"),      # dinner 1h + 30 min travel
    ]


def test_evening_place_without_dinner_starts_at_seven():
    stops = DayPlanner().plan([NIGHT_SAFARI])
    assert (stops[0].time, stops[0].period) == ("19:00", "Evening")


def test_afternoon_place_waits_until_after_lunch():
    stops = DayPlanner().plan([place("Sunny Beach", "afternoon"), place("Museum"),
                               place("Hawker", item_type="food")])

    assert [(stop.time, stop.item.name) for stop in stops] == [
        ("09:00", "Museum"), ("12:00", "Hawker"), ("13:30", "Sunny Beach")]


def test_places_for_any_time_keep_the_users_order():
    stops = DayPlanner().plan([place("Mall A", item_type="shopping"),
                               place("Mall B", item_type="shopping")])
    assert [stop.item.name for stop in stops] == ["Mall A", "Mall B"]


def test_manual_times_are_kept_but_get_a_warning():
    stops = DayPlanner().plan([place("Night Safari", "evening", time="09:00"),
                               place("Singapore Zoo", "morning", time="17:00")])

    assert [stop.time for stop in stops] == ["09:00", "17:00"]   # user's choice stays
    assert "evening" in stops[0].note
    assert "may close" in stops[1].note


def test_morning_place_pushed_late_by_a_full_day_gets_a_warning():
    stops = DayPlanner().plan([place(f"Museum {n}", "morning") for n in range(1, 5)])

    assert stops[0].note == ""
    assert stops[-1].time == "16:30" and "may close" in stops[-1].note


# ---------- where best_time comes from ----------

@pytest.mark.parametrize("given, stored", [
    ("evening", "evening"), ("Morning", "morning"), (" AFTERNOON ", "afternoon"),
    ("midnight", "any"), ("", "any"), (None, "any"),
])
def test_recommendation_cleans_the_ais_best_time(given, stored):
    data = {"name": "X", "type": "activity", "category": "c", "estimated_cost_sgd": 1,
            "location": "l", "environment": "Outdoor", "description": "d",
            "best_time": given}
    recommendation = Recommendation.from_dict(data)

    assert recommendation.best_time == stored
    assert recommendation.to_dict()["best_time"] == stored


def test_older_saved_data_without_best_time_still_loads():
    old = {"name": "X", "type": "activity", "category": "c", "estimated_cost_sgd": 1,
           "location": "l", "environment": "Outdoor", "description": "d"}
    assert Recommendation.from_dict(old).best_time == "any"
    assert ItineraryItem.from_dict({"name": "X", "type": "activity",
                                    "cost_sgd": 1}).best_time == "any"


def test_itinerary_item_keeps_best_time_when_saved_and_loaded():
    item = place("Night Safari", "evening")
    assert ItineraryItem.from_dict(item.to_dict()).best_time == "evening"


def test_prompt_asks_the_ai_for_best_time():
    prompt = PromptBuilder().build("Singapore", {}, category="activity")
    assert '"best_time"' in prompt
    assert '"morning", "afternoon", "evening" or "any"' in prompt