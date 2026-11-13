"""Web loading screen: live progress, cleaned destination and time warnings."""
import json

import pytest

import web_app
from models import Recommendation, RecommendationSet, UserRequirements
from storage.itinerary_manager import ItineraryManager
from storage.itinerary_repository import JsonItineraryRepository
from storage.json_csv_repository import JsonCsvRepository
from user_io.generation_progress import GenerationProgress

FORM = {
    "destination": "sg",
    "max_activity_spend": "100", "max_meal_spend": "30",
    "max_accommodation_spend": "200", "max_shopping_spend": "100",
}


@pytest.fixture
def client():
    web_app.app.config["TESTING"] = True
    return web_app.app.test_client()


# ---------- GenerationProgress on its own ----------

def test_progress_counts_finished_categories_and_remembers_the_model():
    progress = GenerationProgress()
    progress.start("abc12345")
    notify = progress.notifier("abc12345")

    notify("info", "[food] Trying Gemini model: gemini-2.5-flash")
    notify("info", "[food] Gemini succeeded using gemini-2.5-flash.")
    notify("info", "[activity] Groq succeeded using some-model.")

    status = progress.snapshot("abc12345")
    assert status["model"] == "gemini-2.5-flash"
    assert status["categories_done"] == 2
    assert status["categories_total"] == 4
    assert status["finished"] is False

    progress.finish("abc12345")
    assert progress.snapshot("abc12345")["finished"] is True


def test_progress_still_calls_the_original_notifier():
    calls = []
    progress = GenerationProgress()
    progress.start("abc12345")
    progress.notifier("abc12345", also=lambda level, msg: calls.append(msg))("info", "hi")
    assert calls == ["hi"]


@pytest.mark.parametrize("bad_id", ["", "short", "../../etc/passwd", "a" * 65, "id with spaces"])
def test_progress_rejects_strange_ids(bad_id):
    assert GenerationProgress.valid_id(bad_id) is False


def test_unknown_progress_id_gives_404(client):
    assert client.get("/progress/never-started-123").status_code == 404


# ---------- Flask routes ----------

def test_generate_reports_progress_while_the_ai_works(client, monkeypatch):
    seen = {}

    class FakeAssistant:
        def generate_trip(self, requirements, notify=None):
            notify("info", "[activity] Trying Gemini model: gemini-2.5-flash")
            notify("info", "[activity] Gemini succeeded using gemini-2.5-flash.")
            # What the loading screen would see at this moment:
            seen.update(client.get("/progress/test-progress-1").get_json())
            return RecommendationSet(requirements.destination, requirements)

    monkeypatch.setattr(web_app, "TravelAssistant", FakeAssistant)
    monkeypatch.setattr(web_app, "_store_latest_result", lambda result: None)

    response = client.post("/generate", data=dict(FORM, progress_id="test-progress-1"))

    assert response.status_code == 200
    assert seen["categories_done"] == 1
    assert seen["model"] == "gemini-2.5-flash"
    assert client.get("/progress/test-progress-1").get_json()["finished"] is True


def test_validate_inputs_returns_the_cleaned_destination(client):
    result = client.post("/validate-inputs", data=FORM).get_json()
    assert result["valid"] is True
    assert result["destination"] == "Singapore"


@pytest.mark.parametrize("typed, valid, shown", [
    ("sg", True, "Singapore"),
    ("jp", True, "Japan"),
    ("tokyo", True, "Tokyo, Japan"),
    ("qwertyzz", False, ""),
    ("", False, ""),
])
def test_check_destination(client, typed, valid, shown):
    result = client.get("/check-destination", query_string={"destination": typed}).get_json()
    assert result["valid"] is valid
    assert result["destination"] == shown


def test_home_page_has_the_flight_loading_screen(client):
    page = client.get("/").get_data(as_text=True)
    for part in ('id="flight-plane"', 'id="loading-elapsed"', 'id="cancel-button"',
                 'id="destination-note"'):
        assert part in page


def test_itinerary_page_shows_time_warning(monkeypatch, tmp_path):
    requirements = UserRequirements.from_dict({"destination": "Singapore"})
    trip = RecommendationSet("Singapore", requirements)
    trip.add_item(Recommendation(name="Night Safari", item_type="activity",
                                 category="Wildlife", cost_sgd=49.0,
                                 location="Mandai", environment="Outdoor",
                                 description="Nocturnal animals"))
    sets = JsonCsvRepository(str(tmp_path))
    plans = JsonItineraryRepository(str(tmp_path))
    monkeypatch.setattr(web_app, "JsonCsvRepository", lambda: sets)
    monkeypatch.setattr(web_app, "JsonItineraryRepository", lambda: plans)
    set_id = sets.save(trip)
    client = web_app.app.test_client()

    # The user drags the Night Safari to 9am.
    client.post("/itineraries/save", data={
        "set_id": set_id, "title": "Test", "daily_budget": "200",
        "plan": json.dumps([[{"index": 0, "meal": "", "time": "09:00", "duration": 120}]]),
    })
    itinerary_id = ItineraryManager(plans).find()[0]["id"]
    page = client.get(f"/itineraries/{itinerary_id}/view").get_data(as_text=True)

    assert "Usually an evening place" in page