"""Itinerary storage. ItineraryRepository is the interface and
JsonItineraryRepository saves everything into data/itineraries.json."""

import json
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from models import Itinerary


def _now() -> str:
    # Get the current date and time as text
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _summary(identifier: str, data: dict) -> dict:
    """Only the fields needed for the itinerary list page."""
    return {
        "id": identifier,
        "title": data.get("title", ""),
        "destination": data.get("destination", ""),
        "source_id": data.get("source_id", ""),
        "day_count": len(data.get("days", [])),
        "item_count": sum(len(day) for day in data.get("days", [])),
        "daily_budget": data.get("daily_budget", 0),
        "trip_total": data.get("trip_total", 0),
        "over_budget_days": data.get("over_budget_days", []),
        "saved_at": data.get("saved_at", ""),
        "updated_at": data.get("updated_at", ""),
    }
