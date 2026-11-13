"""Auto-planned times must make sense for the place (no zoo at night)."""
import pytest

from models import DayPlanner, ItineraryItem


def place(name, item_type="activity", category="", description="", time=""):
    return ItineraryItem(name, item_type, 10, category=category,
                         description=description, time=time)


NIGHT_SAFARI = place("Night Safari", category="Wildlife",
                     description="Nighttime zoo experience featuring nocturnal animals.")
ZOO = place("Singapore Zoo", category="Nature",
            description="World-class open-concept zoo with over 2,800 animals.")


@pytest.mark.parametrize("item, expected", [
    (NIGHT_SAFARI, "night"),
    (ZOO, "day"),
    (place("Chinatown Night Market", "shopping"), "night"),
    (place("Clarke Quay", category="Nightlife"), "night"),
    (place("National Museum of Singapore"), "day"),
    (place("Skypark", description="Great views by day and night"), "any"),
    (place("Bugis Street Market", "shopping"), "any"),
    (place("Barbecue Corner"), "any"),               # "bar" must be a whole word
    (place("Night Owl Cafe", "food"), "any"),        # meals have their own rules
])
def test_best_time_of_day(item, expected):
    assert DayPlanner.best_time(item) == expected


def test_the_bug_from_the_screenshot_is_fixed():
    # Night Safari added first and the zoo last used to give
    # Night Safari 09:00 and the zoo 17:30.
    stops = DayPlanner().plan([NIGHT_SAFARI, place("Gardens by the Bay"),
                               place("Singapore Flyer"), ZOO])
    times = {stop.item.name: stop.time for stop in stops}

    assert times["Night Safari"] >= "19:00"
    assert times["Singapore Zoo"] < "12:00"      # daytime places go first
    assert all(stop.note == "" for stop in stops)


def test_evening_place_goes_after_dinner():
    stops = DayPlanner().plan([NIGHT_SAFARI, place("Hawker", "food"),
                               place("Restaurant", "food")])

    assert [(stop.time, stop.label, stop.item.name) for stop in stops] == [
        ("12:00", "Lunch", "Hawker"),
        ("18:30", "Dinner", "Restaurant"),
        ("20:00", "", "Night Safari"),      # dinner 1h + 30 min travel
    ]


def test_evening_place_without_dinner_starts_at_seven():
    stops = DayPlanner().plan([NIGHT_SAFARI])
    assert (stops[0].time, stops[0].period) == ("19:00", "Evening")


def test_user_order_is_kept_for_places_that_fit_any_time():
    stops = DayPlanner().plan([place("Mall A", "shopping"), place("Mall B", "shopping")])
    assert [stop.item.name for stop in stops] == ["Mall A", "Mall B"]


def test_manual_times_are_kept_but_get_a_warning():
    stops = DayPlanner().plan([place("Night Safari", time="09:00"),
                               place("Singapore Zoo", time="17:00")])

    assert [stop.time for stop in stops] == ["09:00", "17:00"]   # user's choice stays
    assert "evening place" in stops[0].note
    assert "close around 6pm" in stops[1].note


def test_daytime_place_pushed_late_by_a_full_day_gets_a_warning():
    museums = [place(f"Museum {n}") for n in range(1, 5)]
    stops = DayPlanner().plan(museums)

    assert stops[0].note == ""
    assert stops[-1].time == "16:30" and "6pm" in stops[-1].note