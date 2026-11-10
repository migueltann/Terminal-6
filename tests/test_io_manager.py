"""Tests for the IO components (IOManager and DestinationValidator).

No live AI is needed: typed answers are faked with monkeypatch, and
printed output is captured with capsys.
"""

import pytest

from models import Recommendation, RecommendationSet, RuleResult, UserRequirements
from user_io import DestinationValidator


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