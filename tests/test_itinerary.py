"""Check the itinerary model, its storage and the builder web pages."""

import json

import pytest

import web_app
from models import DayPlanner, Itinerary, ItineraryItem, RecommendationSet
from storage.data_manager import DataManager
from storage.itinerary_manager import ItineraryManager
from storage.itinerary_repository import JsonItineraryRepository
from storage.json_csv_repository import JsonCsvRepository


def make_item(name, item_type, cost):
    return {
        "name": name, "type": item_type, "category": "Test",
        "estimated_cost_sgd": cost, "location": "Singapore",
        "environment": "Outdoor", "description": "A test item",
        "checks": [{"label": "Budget", "passed": True, "detail": "OK"}],
    }


@pytest.fixture
def trip():
    """A saved set with 4 approved items (positions 0-3 in approved())."""
    return RecommendationSet.from_dict({
        "destination": "Singapore",
        "requirements": {"destination": "Singapore"},
        "activities": [make_item("Gardens by the Bay", "activity", 28)],
        "food": [make_item("Maxwell Food Centre", "food", 8)],
        "accommodation": [make_item("Champion Hotel", "accommodation", 130)],
        "shopping": [make_item("Bugis Street Market", "shopping", 40)],
    })


def names(day):
    return [item.name for item in day]


# ---------- model: building and budget logic ----------

def test_from_selection_uses_prices_from_the_saved_set(trip):
    plan = Itinerary.from_selection(trip, "set-1", 200, [[0, 1], [2], []])

    assert plan.title == "Singapore"
    assert names(plan.days[0]) == ["Gardens by the Bay", "Maxwell Food Centre"]
    assert plan.day_total(0) == 36
    assert plan.day_total(2) == 0
    assert plan.trip_total() == 166
    assert plan.trip_budget() == 600


def test_same_item_can_be_added_on_several_days(trip):
    plan = Itinerary.from_selection(trip, "set-1", 200, [[2], [2], [2]])

    assert plan.trip_total() == 390


def test_over_budget_days_are_numbered_from_one(trip):
    plan = Itinerary.from_selection(trip, "set-1", 100, [[0], [2], [2, 3]])

    assert plan.over_budget_days() == [2, 3]
    assert not plan.is_over_budget(0)


def test_exactly_on_budget_is_not_over(trip):
    plan = Itinerary.from_selection(trip, "set-1", 36, [[0, 1]])

    assert plan.over_budget_days() == []


@pytest.mark.parametrize("selection", [
    [[99]], [[-1]], [["0"]], [[True]], [[1.0]], "not a list", [1, 2],
])
def test_invalid_selection_is_rejected(trip, selection):
    with pytest.raises(ValueError):
        Itinerary.from_selection(trip, "set-1", 200, selection)


@pytest.mark.parametrize("days, budget", [
    ([], 200),                       # no days
    ([[]] * 15, 200),                # too many days
    ([[]], -1),                      # negative budget
    ([[]], float("nan")),            # not a number
    ([[]], float("inf")),
    ([[ItineraryItem("x", "food", 1)] * 31], 200),   # too many items in a day
])
def test_invalid_itinerary_is_rejected(days, budget):
    with pytest.raises(ValueError):
        Itinerary("Trip", "Singapore", "set-1", budget, days)


def test_blank_title_falls_back_to_destination():
    assert Itinerary("   ", "Tokyo", "set-1", 100, [[]]).title == "Tokyo"


def test_add_and_remove_item():
    plan = Itinerary("Trip", "Singapore", "set-1", 100, [[], []])
    plan.add_item(1, ItineraryItem("Lau Pa Sat", "food", 15))

    assert plan.day_total(1) == 15
    assert plan.remove_item(1, 0).name == "Lau Pa Sat"
    assert plan.trip_total() == 0


def test_dict_round_trip(trip):
    # day 1 = 28 + 40 = 68, day 2 = 130 (over a 100 budget)
    plan = Itinerary.from_selection(trip, "set-1", 100, [[0, 3], [2]], "Weekend")
    copy = Itinerary.from_dict(json.loads(json.dumps(plan.to_dict())))

    assert copy == plan
    assert plan.to_dict()["over_budget_days"] == [2]


def test_selection_for_maps_items_back_to_positions(trip):
    plan = Itinerary.from_selection(trip, "set-1", 200, [[3, 0], [], [1]])

    assert plan.selection_for(trip) == [
        [{"index": 3, "meal": "", "time": "", "duration": 0}, {"index": 0, "meal": "", "time": "", "duration": 0}],
        [],
        [{"index": 1, "meal": "", "time": "", "duration": 0}],
    ]


def test_meal_choice_is_kept_and_reopens_in_the_builder(trip):
    # position 1 is Maxwell Food Centre (food)
    plan = Itinerary.from_selection(trip, "set-1", 200, [[0, {"index": 1, "meal": "dinner", "time": "", "duration": 0}]])
    copy = Itinerary.from_dict(json.loads(json.dumps(plan.to_dict())))

    assert copy.days[0][1].meal == "dinner"
    assert copy.selection_for(trip) == [[{"index": 0, "meal": "", "time": "", "duration": 0},
                                         {"index": 1, "meal": "dinner", "time": "", "duration": 0}]]


@pytest.mark.parametrize("entry", [
    {"index": 1, "meal": "breakfast", "time": "", "duration": 0}, {"index": 1, "meal": None}, {"meal": "lunch"},
])
def test_invalid_meal_choice_is_rejected(trip, entry):
    with pytest.raises(ValueError):
        Itinerary.from_selection(trip, "set-1", 200, [[entry]])


def test_meal_is_ignored_for_non_food_items(trip):
    # position 0 is an activity, so a meal choice makes no sense
    plan = Itinerary.from_selection(trip, "set-1", 200, [[{"index": 0, "meal": "lunch", "time": "", "duration": 0}]])

    assert plan.days[0][0].meal == ""


def test_selection_for_skips_items_no_longer_in_the_set(trip):
    plan = Itinerary("Trip", "Singapore", "set-1", 200,
                     [[ItineraryItem("Gone", "food", 5),
                       ItineraryItem("Maxwell Food Centre", "food", 8)]])

    assert plan.selection_for(trip) == [[{"index": 1, "meal": "", "time": "", "duration": 0}]]


# ---------- storage (JSON file in pytest's temporary folder) ----------

@pytest.fixture
def manager(tmp_path):
    return ItineraryManager(JsonItineraryRepository(str(tmp_path)))


def test_damaged_file_is_handled(tmp_path):
    (tmp_path / "itineraries.json").write_text("{not json", encoding="utf-8")
    manager = ItineraryManager(JsonItineraryRepository(str(tmp_path)))

    assert manager.load("anything") is None
    assert manager.delete("anything") is False
    with pytest.raises(ValueError):
        manager.find()


def test_crud(manager, trip):
    plan = manager.build(trip, "set-1", 200, [[0], [1, 2]], "SG trip")

    identifier = manager.save(plan)                               # Create
    assert manager.load(identifier) == plan                       # Read one

    entries = manager.find()                                      # Read all
    assert len(entries) == 1
    assert entries[0]["id"] == identifier
    assert entries[0]["title"] == "SG trip"
    assert entries[0]["day_count"] == 2
    assert entries[0]["item_count"] == 3
    assert entries[0]["trip_total"] == 166
    assert entries[0]["saved_at"]

    changed = manager.build(trip, "set-1", 100, [[2]], "SG short")
    assert manager.update(identifier, changed) is True            # Update
    assert manager.load(identifier).title == "SG short"
    entry = manager.find()[0]
    assert entry["over_budget_days"] == [1]
    assert entry["saved_at"] == entries[0]["saved_at"]
    assert entry["updated_at"]

    assert manager.delete(identifier) is True                     # Delete
    assert manager.load(identifier) is None
    assert manager.find() == []


def test_find_matches_title_or_destination(manager, trip):
    manager.save(manager.build(trip, "set-1", 200, [[0]], "Honeymoon"))

    assert len(manager.find("honey")) == 1
    assert len(manager.find("SINGA")) == 1
    assert manager.find("tokyo") == []


@pytest.mark.parametrize("identifier", ["", "nope", "6731a8f2c4e5d6b7a8f9e0d1"])
def test_unknown_identifier(manager, trip, identifier):
    plan = manager.build(trip, "set-1", 200, [[0]])

    assert manager.load(identifier) is None
    assert manager.update(identifier, plan) is False
    assert manager.delete(identifier) is False


# ---------- web pages ----------

@pytest.fixture
def web(monkeypatch, tmp_path, trip):
    """A Flask test client that stores everything in a temporary folder."""
    sets = JsonCsvRepository(str(tmp_path))
    plans = JsonItineraryRepository(str(tmp_path))
    monkeypatch.setattr(web_app, "JsonCsvRepository", lambda: sets)
    monkeypatch.setattr(web_app, "JsonItineraryRepository", lambda: plans)
    set_id = sets.save(trip)
    web_app.app.config["TESTING"] = True
    return web_app.app.test_client(), set_id, ItineraryManager(plans), sets


def test_builder_page_lists_approved_items(web):
    client, set_id, _, _ = web

    page = client.get(f"/itineraries/new/{set_id}").get_data(as_text=True)

    assert "Gardens by the Bay" in page
    assert "Champion Hotel" in page
    assert "Create itinerary" in page


def test_builder_for_unknown_set_redirects(web):
    client, _, _, _ = web

    response = client.get("/itineraries/new/does-not-exist")

    assert response.status_code == 302


def test_save_then_reopen_then_update(web):
    client, set_id, plans, _ = web

    response = client.post("/itineraries/save", data={
        "set_id": set_id, "title": "My trip", "daily_budget": "100",
        "plan": json.dumps([[0, 1], [2]]),
    }, follow_redirects=True)
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Itinerary saved." in page
    assert "Over the daily budget on day 2." in page

    saved = plans.find()
    assert len(saved) == 1
    assert saved[0]["trip_total"] == 166
    identifier = saved[0]["id"]

    page = client.get(f"/itineraries/{identifier}").get_data(as_text=True)
    assert "Update itinerary" in page

    client.post("/itineraries/save", data={
        "set_id": set_id, "itinerary_id": identifier, "title": "Renamed",
        "daily_budget": "300", "plan": json.dumps([[2]]),
    })

    assert plans.find()[0]["title"] == "Renamed"
    assert len(plans.find()) == 1


@pytest.mark.parametrize("form", [
    {"plan": "not json", "daily_budget": "100"},
    {"plan": "[[99]]", "daily_budget": "100"},
    {"plan": "[[0]]", "daily_budget": "-5"},
    {"plan": "[[0]]", "daily_budget": "abc"},
])
def test_bad_submissions_are_rejected(web, form):
    client, set_id, plans, _ = web

    response = client.post("/itineraries/save",
                           data={"set_id": set_id, "title": "x", **form})

    assert response.status_code == 302
    assert plans.find() == []


def test_list_and_delete(web):
    client, set_id, plans, _ = web
    identifier = plans.save(plans.build(
        DataManager(web[3]).load(set_id), set_id, 200, [[0]], "Listed trip"))

    assert "Listed trip" in client.get("/itineraries").get_data(as_text=True)

    client.post(f"/itineraries/{identifier}/delete")

    assert plans.find() == []


def test_itinerary_can_still_be_viewed_after_its_set_is_deleted(web):
    client, set_id, plans, sets = web
    identifier = plans.save(plans.build(
        DataManager(sets).load(set_id), set_id, 200, [[0]], "Orphan"))
    sets.delete(set_id)

    # Editing is no longer possible, so the user is sent to the view page.
    response = client.get(f"/itineraries/{identifier}", follow_redirects=True)
    page = response.get_data(as_text=True)

    assert "can no longer be edited" in page
    assert "Gardens by the Bay" in page
    assert "Edit plan" not in page
    assert "Update itinerary" not in page


def test_saving_opens_the_finished_itinerary(web):
    client, set_id, plans, _ = web

    response = client.post("/itineraries/save", data={
        "set_id": set_id, "title": "Weekend", "daily_budget": "200",
        "start_date": "2026-12-14",
        # day 1: Gardens (activity), Maxwell (food), Champion Hotel (stay)
        "plan": json.dumps([[0, 1, 2], []]),
    })

    identifier = plans.find()[0]["id"]
    assert response.headers["Location"].endswith(f"/itineraries/{identifier}/view")

    page = client.get(response.headers["Location"]).get_data(as_text=True)

    assert "2-day trip to Singapore" in page
    assert "14 Dec – 15 Dec 2026" in page
    assert "Monday, 14 December 2026" in page
    assert "09:00" in page and "Lunch" in page and "12:00" in page
    assert "TONIGHT" in page and "Champion Hotel" in page
    assert "Free day" in page                                   # day 2 is empty
    assert "A test item" in page                                # description shown
    assert "google.com/maps/search/?api=1&amp;query=Gardens+by+the+Bay" in page
    assert "Budget summary" in page
    assert "Edit plan" in page


def test_view_of_unknown_itinerary_redirects(web):
    client, _, _, _ = web

    assert client.get("/itineraries/nope/view").status_code == 302


def test_invalid_start_date_is_rejected(web):
    client, set_id, plans, _ = web

    client.post("/itineraries/save", data={
        "set_id": set_id, "title": "x", "daily_budget": "100",
        "start_date": "2026-02-30", "plan": "[[0]]",
    })

    assert plans.find() == []


# ---------- day planner: turning picks into a timed schedule ----------

def item(name, item_type, meal=""):
    return ItineraryItem(name, item_type, 10, meal=meal)


def timeline(stops):
    return [(stop.time, stop.label, stop.item.name) for stop in stops]


def test_planner_builds_a_realistic_day():
    stops = DayPlanner().plan([
        item("Hotel", "accommodation"),
        item("Museum", "activity"),
        item("Hawker", "food"),
        item("Garden", "activity"),
        item("Mall", "shopping"),
        item("Restaurant", "food"),
    ])

    assert timeline(stops) == [
        ("09:00", "", "Museum"),          # 2h + 30 min travel
        ("11:30", "", "Garden"),          # first half of visits = morning
        ("14:00", "Lunch", "Hawker"),     # already past 12:00
        ("15:30", "", "Mall"),
        ("18:30", "Dinner", "Restaurant"),
        ("", "Stay", "Hotel"),            # accommodation goes last
    ]
    assert [stop.period for stop in stops] == [
        "Morning", "Morning", "Afternoon", "Afternoon", "Evening", "Overnight"]


def test_lunch_waits_until_noon():
    stops = DayPlanner().plan([item("Museum", "activity"), item("Cafe", "food")])

    assert timeline(stops) == [("09:00", "", "Museum"), ("12:00", "Lunch", "Cafe")]


def test_extra_meals_come_after_dinner():
    stops = DayPlanner().plan([item("A", "food"), item("B", "food"), item("C", "food")])

    assert [stop.label for stop in stops] == ["Lunch", "Dinner", "Extra meal"]
    assert stops[2].time == "20:00"


def test_day_can_skip_lunch_and_only_have_dinner():
    stops = DayPlanner().plan([item("Museum", "activity"),
                               item("Steakhouse", "food", "dinner")])

    assert timeline(stops) == [("09:00", "", "Museum"), ("18:30", "Dinner", "Steakhouse")]


def test_marked_meals_override_the_order_they_were_added():
    stops = DayPlanner().plan([item("Steakhouse", "food", "dinner"),
                               item("Hawker", "food", "lunch")])

    assert timeline(stops) == [("12:00", "Lunch", "Hawker"),
                               ("18:30", "Dinner", "Steakhouse")]


def test_auto_food_fills_the_slot_that_is_still_empty():
    stops = DayPlanner().plan([item("Cafe", "food"), item("Hawker", "food", "lunch")])

    assert timeline(stops) == [("12:00", "Lunch", "Hawker"), ("18:30", "Dinner", "Cafe")]


def timed(name, item_type, time, meal=""):
    return ItineraryItem(name, item_type, 10, meal=meal, time=time)


def test_places_on_the_timeline_keep_their_time():
    stops = DayPlanner().plan([timed("Night market", "shopping", "20:00"),
                               timed("Zoo", "activity", "08:00")])

    assert timeline(stops) == [("08:00", "", "Zoo"), ("20:00", "", "Night market")]
    assert [stop.period for stop in stops] == ["Morning", "Evening"]


def test_untimed_places_are_fitted_around_timed_ones():
    # The zoo is 09:00-11:30 (2h + travel), so the museum has to wait until 11:30.
    stops = DayPlanner().plan([item("Museum", "activity"),
                               timed("Zoo", "activity", "09:00")])

    assert timeline(stops) == [("09:00", "", "Zoo"), ("11:30", "", "Museum")]


def test_timed_food_is_labelled_by_time_of_day():
    stops = DayPlanner().plan([timed("Kaya toast", "food", "08:00"),
                               timed("Hawker", "food", "13:00"),
                               timed("Steakhouse", "food", "19:00")])

    assert [stop.label for stop in stops] == ["Breakfast", "Lunch", "Dinner"]


def test_timed_lunch_means_auto_food_becomes_dinner():
    stops = DayPlanner().plan([item("Cafe", "food"), timed("Hawker", "food", "12:00")])

    assert timeline(stops) == [("12:00", "Lunch", "Hawker"), ("18:30", "Dinner", "Cafe")]


@pytest.mark.parametrize("bad_time", ["9:00", "24:00", "12:60", "noon", "12-00"])
def test_invalid_time_is_rejected(bad_time):
    with pytest.raises(ValueError):
        ItineraryItem("Zoo", "activity", 10, time=bad_time)


def test_a_stay_ignores_any_time():
    assert ItineraryItem("Hotel", "accommodation", 100, time="15:00").time == ""


def test_chosen_duration_sets_the_end_time_and_blocks_that_time():
    # Bugis Street 09:00 for 3 hours, so the museum can't start until 12:30.
    stops = DayPlanner().plan([
        item("Museum", "activity"),
        ItineraryItem("Bugis Street", "shopping", 10, time="09:00", duration=180),
    ])

    assert [(stop.time, stop.end, stop.item.name) for stop in stops] == [
        ("09:00", "12:00", "Bugis Street"),
        ("12:30", "14:30", "Museum"),     # usual 2 hours for an activity
    ]


@pytest.mark.parametrize("bad_duration", [-60, 24 * 60 + 1, 1.5, "60", True])
def test_invalid_duration_is_rejected(bad_duration):
    with pytest.raises(ValueError):
        ItineraryItem("Zoo", "activity", 10, time="09:00", duration=bad_duration)


def test_web_builder_saves_the_chosen_time(web):
    client, set_id, plans, _ = web
    client.post("/itineraries/save", data={
        "set_id": set_id, "title": "Timed", "daily_budget": "200",
        "plan": json.dumps([[{"index": 0, "meal": "", "time": "15:00", "duration": 120}]]),
    })

    saved = plans.load(plans.find()[0]["id"])
    assert saved.days[0][0].time == "15:00"
    assert saved.days[0][0].duration == 120
    assert (saved.schedule(0)[0].time, saved.schedule(0)[0].end) == ("15:00", "17:00")


def test_web_builder_saves_the_meal_choice(web):
    client, set_id, plans, _ = web
    client.post("/itineraries/save", data={
        "set_id": set_id, "title": "Dinner only", "daily_budget": "200",
        "plan": json.dumps([[{"index": 1, "meal": "dinner", "time": "", "duration": 0}]]),
    })

    saved = plans.load(plans.find()[0]["id"])
    assert saved.days[0][0].meal == "dinner"


def test_empty_day_has_no_stops():
    assert DayPlanner().plan([]) == []


def test_dates_follow_the_start_date(trip):
    plan = Itinerary.from_selection(trip, "set-1", 200, [[], [], []],
                                    start_date="2026-12-31")

    assert str(plan.date_for(0)) == "2026-12-31"
    assert str(plan.date_for(2)) == "2027-01-02"
    assert Itinerary("x", "y", "z", 1, [[]]).date_for(0) is None


def test_snapshot_keeps_description_and_category(trip):
    plan = Itinerary.from_selection(trip, "set-1", 200, [[0]])
    copy = Itinerary.from_dict(plan.to_dict())

    assert copy.days[0][0].description == "A test item"
    assert copy.days[0][0].category == "Test"


def test_older_saved_itineraries_still_load():
    """Itineraries saved before descriptions and dates were added."""
    plan = Itinerary.from_dict({
        "title": "Old", "destination": "Tokyo", "source_id": "s",
        "daily_budget": 100,
        "days": [[{"name": "Shrine", "type": "activity", "cost_sgd": 0, "location": ""}]],
    })

    assert plan.start_date == ""
    assert plan.days[0][0].description == ""


def test_overlapping_manual_times_are_rejected():
    """Two manually scheduled activities must not overlap."""

    items = [
        ItineraryItem(
            "Bugis Street", "shopping", 10,
            time="09:00", duration=180
        ),
        ItineraryItem(
            "Museum", "activity", 20,
            time="10:00", duration=120
        ),
    ]

    with pytest.raises(ValueError, match="Scheduling conflict"):
        DayPlanner().plan(items)


def test_overlapping_activities_are_rejected_by_flask(web):
    """Flask must reject overlapping activities before saving."""

    client, set_id, plans, _ = web

    # Two activities on the same day with overlapping times.
    selection = [[
        {"index": 0, "time": "09:00", "duration": 180},
        {"index": 3, "time": "10:00", "duration": 120},
    ]]

    response = client.post(
        "/itineraries/save",
        data={
            "set_id": set_id,
            "title": "Overlapping trip",
            "daily_budget": "200",
            "plan": json.dumps(selection),
        },
    )

    # Flask should redirect instead of crashing.
    assert response.status_code == 302

    # The invalid itinerary must not be saved.
    assert plans.find() == []

    # The error should be displayed to the user.
    with client.session_transaction() as session:
        messages = session.get("_flashes", [])

    assert any(
        "Scheduling conflict" in message
        for category, message in messages
    )
    assert any(
        "Day 1" in message
        for category, message in messages
    )

@pytest.mark.parametrize("contents", ["{}", "null", '["invalid"]'])
def test_invalid_storage_is_not_overwritten(tmp_path, contents):
    path = tmp_path / "itineraries.json"
    path.write_text(contents, encoding="utf-8")

    repository = JsonItineraryRepository(str(tmp_path))
    itinerary = Itinerary("Trip", "Singapore", "set-1", 100)

    with pytest.raises(ValueError, match="list of dictionaries"):
        repository.save(itinerary)

    assert path.read_text(encoding="utf-8") == contents