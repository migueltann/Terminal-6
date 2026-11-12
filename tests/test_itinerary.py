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
