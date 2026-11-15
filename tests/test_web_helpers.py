"""Tests for the helper classes used by the Flask web interface."""
from flask import Flask
from werkzeug.datastructures import MultiDict

from models import ItineraryItem
from web import AIErrorTranslator, ItineraryPresenter, LatestResultStore, WebInputValidator


class FakeDestinations:
    """Stands in for DestinationValidator so no geonames data is loaded."""

    def validate(self, text):
        if text.lower() in {"sg", "singapore"}:
            return "Singapore", None
        return None, f"'{text}' is not a valid country or city."


def valid_form(**changes):
    data = {"destination": "sg", "preferred_activities": "museums, any",
            "max_activity_spend": "50", "max_meal_spend": "20",
            "max_accommodation_spend": "150", "max_shopping_spend": "80",
            "activity_environment": "outdoor", "preferred_transport": "transit",
            "dietary": "Other", "dietary_custom": "gluten-free"}
    data.update(changes)
    return MultiDict(data)


def test_input_validator_cleans_a_valid_form():
    data, errors, _ = WebInputValidator(FakeDestinations()).collect(valid_form())

    assert errors == []
    assert data["destination"] == "Singapore"
    assert data["preferred_activities"] == []        # "any" means no preference
    assert data["activity_environment"] == "Outdoor"
    assert data["preferred_transport"] == "Transit"
    assert data["dietary"] == "gluten-free"


def test_input_validator_rejects_bad_budget_destination_and_transport():
    form = valid_form(destination="Atlantis", max_meal_spend="-5",
                      max_shopping_spend="inf", preferred_transport="rocket")
    _, errors, field_errors = WebInputValidator(FakeDestinations()).collect(form)

    assert {"destination", "max_meal_spend", "max_shopping_spend",
            "preferred_transport"} <= field_errors.keys()
    assert len(errors) == 4


def test_error_translator_gives_friendly_messages():
    assert "no Groq backup" in AIErrorTranslator.friendly(
        RuntimeError("All AI providers failed. Groq: GROQ_API_KEY environment variable is missing."))
    assert "timed out" in AIErrorTranslator.friendly(RuntimeError("Read timeout"))
    assert AIErrorTranslator.friendly(RuntimeError("odd")).endswith("odd")


def test_result_store_rejects_unsafe_keys_and_round_trips(tmp_path):
    app = Flask(__name__)
    app.secret_key = "test"
    store = LatestResultStore(str(tmp_path))

    assert store._path_for("../../secret") is None
    assert store._path_for("") is None

    with app.test_request_context():
        assert store.load() is None             # nothing saved yet
        store.save({"destination": "Singapore"})
        assert store.load() == {"destination": "Singapore"}
        store.clear()
        assert store.load() is None


def test_presenter_builds_a_safe_maps_link():
    item = ItineraryItem(name="Satay & Co", item_type="food", cost_sgd=10,
                         location="Lau Pa Sat")
    link = ItineraryPresenter.maps_link(item, "Singapore")
    assert link.endswith("Satay+%26+Co%2C+Lau+Pa+Sat%2C+Singapore")