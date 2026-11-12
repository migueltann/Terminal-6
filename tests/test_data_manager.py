"""Check the data manager and its JSON/CSV repository together."""

import csv
from pathlib import Path

import pytest

from storage.data_manager import DataManager
from models import RecommendationSet
from storage.json_csv_repository import JsonCsvRepository
from storage.recommendation_repository import RecommendationRepository


@pytest.fixture
def manager(tmp_path):
    """Store test files in pytest's temporary folder."""
    return DataManager(JsonCsvRepository(str(tmp_path)))


@pytest.fixture
def sample_result():
    """Make an approved top pick and a rejected recommendation."""
    approved = {
        "name": "Garden Walk",
        "type": "activity",
        "category": "Nature",
        "estimated_cost_sgd": 10,
        "location": "Singapore",
        "environment": "Outdoor",
        "description": "A relaxing garden walk",
        "tags": ["nature", "walking"],
        "transport_options": ["transit"],
        "dietary_tags": [],
        "checks": [
            {"label": "Activity budget", "passed": True, "detail": "Within budget"}
        ],
        "top_pick": True,
        "top_pick_reason": "Affordable nature activity",
    }
    rejected = {
        **approved,
        "name": "Expensive Tour",
        "estimated_cost_sgd": 200,
        "checks": [
            {"label": "Activity budget", "passed": False, "detail": "Over budget"}
        ],
        "top_pick": False,
        "top_pick_reason": "",
    }
    return RecommendationSet.from_dict({
        "destination": "Singapore",
        "requirements": {"destination": "Singapore", "max_activity_spend": 100},
        "activities": [approved],
        "filtered_out": [rejected],
    })


def test_repository_interface_is_abstract():
    with pytest.raises(TypeError):
        RecommendationRepository()


def test_save_creates_json_csv_and_index(manager, sample_result):
    identifier = manager.save(sample_result)
    entries = manager.find()

    assert len(entries) == 1
    entry = entries[0]
    assert entry["filename"] == identifier
    assert entry["approved_count"] == 1
    assert Path(entry["json_path"]).is_file()
    assert Path(entry["csv_path"]).is_file()

    with open(entry["csv_path"], newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    # CSV should include approved items only and readable list values.
    assert len(rows) == 1
    assert rows[0]["name"] == "Garden Walk"
    assert rows[0]["tags"] == "nature, walking"
    assert rows[0]["passed_rules"] == "Activity budget"


def test_load_restores_saved_result(manager, sample_result):
    identifier = manager.save(sample_result)
    loaded = manager.load(identifier)

    assert loaded is not None
    # This checks requirements, approved/rejected items, checks and top picks.
    assert loaded.to_dict() == sample_result.to_dict()


def test_find_ignores_case_and_extra_spaces(manager, sample_result):
    identifier = manager.save(sample_result)
    matches = manager.find("  SINGA  ")

    assert len(matches) == 1
    assert matches[0]["filename"] == identifier
    assert manager.find("Tokyo") == []


def test_delete_removes_files_and_index_entry(manager, sample_result):
    identifier = manager.save(sample_result)
    entry = manager.find()[0]

    assert manager.delete(identifier) is True
    assert not Path(entry["json_path"]).exists()
    assert not Path(entry["csv_path"]).exists()
    assert manager.find() == []
    assert manager.load(identifier) is None


def test_missing_identifier_is_handled(manager):
    assert manager.load("missing.json") is None
    assert manager.delete("missing.json") is False


def test_rename_rewrites_files_and_index(manager, sample_result):
    identifier = manager.save(sample_result)

    assert manager.rename(identifier, "Singapore Weekend") is True

    entry = manager.find()[0]
    assert entry["filename"] == identifier
    assert entry["destination"] == "Singapore Weekend"
    assert manager.load(identifier).destination == "Singapore Weekend"


def test_update_unknown_identifier_returns_false(manager, sample_result):
    assert manager.update("missing.json", sample_result) is False
    assert manager.rename("missing.json", "New name") is False


def test_rename_rejects_blank_name(manager, sample_result):
    identifier = manager.save(sample_result)

    with pytest.raises(ValueError):
        manager.rename(identifier, "   ")


def test_two_saves_create_separate_sets(manager, sample_result):
    first = manager.save(sample_result)
    second = manager.save(sample_result)

    assert first != second
    assert len(manager.find()) == 2
    assert manager.load(first) is not None
    assert manager.load(second) is not None
