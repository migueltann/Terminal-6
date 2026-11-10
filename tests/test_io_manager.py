"""Tests for the IO components (IOManager and DestinationValidator).

No live AI is needed: typed answers are faked with monkeypatch, and
printed output is captured with capsys.
"""

import pytest

from models import Recommendation, RecommendationSet, RuleResult, UserRequirements
from user_io import DestinationValidator, IOManager


@pytest.fixture(scope="module")
def validator():
    return DestinationValidator()


# ---------- DestinationValidator ----------

def test_country_name_is_accepted(validator):
    assert validator.validate("Japan") == ("Japan", None)


def test_country_code_is_accepted(validator):
    destination, error = validator.validate("SG")
    assert destination == "Singapore" and error is None


def test_city_and_country_is_accepted(validator):
    destination, error = validator.validate("paris, france")
    assert destination == "Paris, France" and error is None


def test_empty_destination_is_rejected(validator):
    destination, error = validator.validate("   ")
    assert destination is None and error == "Please enter a destination."


def test_typo_gets_a_suggestion(validator):
    destination, error = validator.validate("Japn")
    assert destination is None
    assert "Did you mean Japan?" in error


def test_city_not_in_that_country_is_rejected(validator):
    destination, error = validator.validate("Paris, Japan")
    assert destination is None
    assert "Could not find 'Paris' in Japan" in error

# ---------- helpers ----------

def fake_input(monkeypatch, answers):
    """Make input() return each answer in turn, like a user typing them."""
    typed = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(typed))


# One answer for each of the 15 questions, in the order they are asked
FULL_ANSWERS = [
    "Japan",          # destination
    "museums, hiking",  # preferred activities
    "80",             # activity budget
    "outdoor",        # activity environment
    "Japanese",       # cuisine preferences
    "30",             # meal budget
    "",               # food environment -> Any
    "halal",          # dietary
    "hotel",          # accommodation preferences
    "200",            # accommodation budget
    "",               # shopping preferences -> Any
    "100",            # shopping budget
    "Indoor",         # shopping environment
    "transit",        # transport
    "nightlife",      # avoid list
]


@pytest.fixture
def io():
    return IOManager()


# ---------- collecting input ----------

def test_collect_requirements_returns_user_requirements(monkeypatch, io):
    fake_input(monkeypatch, FULL_ANSWERS)
    reqs = io.collect_requirements()

    assert isinstance(reqs, UserRequirements)
    assert reqs.destination == "Japan"
    assert reqs.budget_for("activity") == 80.0
    assert reqs.preferences_for("activity") == ["museums", "hiking"]
    assert reqs.preferences_for("shopping") == []          # blank -> Any -> empty list
    assert reqs.environment_for("activity") == "Outdoor"   # typed 'outdoor', stored as option name
    assert reqs.environment_for("food") == "Any"
    assert reqs.dietary == "Halal"
    assert reqs.transport == "Transit"
    assert reqs.avoid_list == ["nightlife"]


def test_exit_returns_none(monkeypatch, io):
    fake_input(monkeypatch, ["Japan", "exit"])
    assert io.collect_requirements() is None


def test_back_goes_to_previous_question(monkeypatch, io):
    # answer destination, then go back and change it to France
    fake_input(monkeypatch, ["Japan", "back", "France"] + FULL_ANSWERS[1:])
    reqs = io.collect_requirements()
    assert reqs.destination == "France"


def test_invalid_budget_asks_again(monkeypatch, io, capsys):
    fake_input(monkeypatch, ["-5", "abc", "0", "45"])
    assert io._ask_positive_float("Budget: ") == 45.0
    assert capsys.readouterr().out.count("Please enter a valid positive amount.") == 3


def test_invalid_destination_asks_again(monkeypatch, io, capsys):
    fake_input(monkeypatch, ["Qwertyzz", "Japan"])
    assert io._ask_destination() == "Japan"
    assert "is not a valid country or city" in capsys.readouterr().out


def test_any_in_a_list_means_no_preference(io):
    cleaned = io._clean_inputs({"preferred_activities": ["Any"], "avoid_list": ["none"],
                                "dietary": "", "preferred_transport": "any"})
    assert cleaned["preferred_activities"] == []
    assert cleaned["avoid_list"] == []
    assert cleaned["dietary"] == "None"
    assert cleaned["preferred_transport"] == "Any"