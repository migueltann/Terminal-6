"""Tests for the LogicManager class (filtering/logic_manager.py).

The old procedural tests stay in tests/test_logic_manager.py.
No AI is needed: recommendations are made by hand.
"""

import pytest

from filtering import LogicManager
from models import Recommendation, RecommendationSet, UserRequirements


# ---------- helpers ----------

def make_requirements(**changes):
    data = {
        "destination": "Singapore",
        "max_activity_spend": 100,
        "max_meal_spend": 40,
        "max_accommodation_spend": 200,
        "max_shopping_spend": 80,
        "activity_environment": "Outdoor",
        "food_environment": "Indoor",
        "shopping_environment": "Indoor",
        "dietary": "halal",
        "preferred_transport": "transit",
        "avoid_list": [],
    }
    data.update(changes)
    return UserRequirements.from_dict(data)


def make_item(item_type="activity", **changes):
    data = {
        "name": "Test Recommendation",
        "type": item_type,
        "category": "General",
        "estimated_cost_sgd": 30,
        "location": "Singapore",
        "environment": "Outdoor" if item_type == "activity" else "Indoor",
        "description": "A sample recommendation",
        "tags": [],
        "transport_options": ["transit", "walk"],
        "dietary_tags": ["halal"],
    }
    data.update(changes)
    return Recommendation.from_dict(data)


@pytest.fixture
def logic():
    return LogicManager()


# ---------- setting up ----------

def test_logic_manager_uses_all_five_rules(logic):
    labels = [rule.label for rule in logic._default_rules()]
    assert labels == ["Budget", "Environment", "Avoid list",
                      "Dietary requirement", "Transport preference"]

# ---------- processing ----------

def test_process_returns_a_recommendation_set(logic):
    result = logic.process(make_requirements(), [make_item()])
    assert isinstance(result, RecommendationSet)
    assert result.destination == "Singapore"


def test_process_separates_approved_and_rejected(logic):
    cheap = make_item(name="Cheap Walk")
    pricey = make_item(name="Pricey Tour", estimated_cost_sgd=500)

    result = logic.process(make_requirements(), [cheap, pricey])

    assert [item.name for item in result.approved()] == ["Cheap Walk"]
    assert [item.name for item in result.rejected_items()] == ["Pricey Tour"]


def test_process_records_every_rule_check_on_the_item(logic):
    result = logic.process(make_requirements(), [make_item("food")])
    labels = [check.label for check in result.approved()[0].results]
    assert "Meal budget" in labels
    assert "Dietary requirement" in labels