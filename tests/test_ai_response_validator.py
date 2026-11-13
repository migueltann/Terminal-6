
import pytest

from ai.ai_response_validator import AIResponseValidator



def make_valid_items():
    """Create 60 complete recommendations, 15 per category."""
    items = []

    for category in ("activity", "food", "accommodation", "shopping"):
        for i in range(15):
            items.append({
                "name": f"{category} {i}",
                "type": category,
                "category": "General",
                "estimated_cost_sgd": 30,
                "location": "Singapore",
                "environment": "Indoor",
                "description": "A sample recommendation",
                "tags": [],
                "transport_options": ["transit"],
                "dietary_tags": ["halal"],
            })

    return items



def test_validator_accepts_correct_structure():
    items = make_valid_items()

    result = AIResponseValidator().validate_response_schema(items)

    assert len(result) == 60


def test_validator_rejects_wrong_count():
    items = make_valid_items()[:59]

    with pytest.raises(RuntimeError):
        AIResponseValidator().validate_response_schema(items)


def test_validator_rejects_wrong_category_distribution():
    items = make_valid_items()
    items[0]["type"] = "food"

    with pytest.raises(RuntimeError):
        AIResponseValidator().validate_response_schema(items)


def test_validator_rejects_non_dictionary_item():
    items = make_valid_items()
    items[0] = "Invalid recommendation"

    with pytest.raises(RuntimeError):
        AIResponseValidator().validate_response_schema(items)


def test_validator_rejects_missing_required_field():
    items = make_valid_items()

    # Simulate Gemini forgetting the environment field
    del items[0]["environment"]

    with pytest.raises(RuntimeError):
        AIResponseValidator().validate_response_schema(items)


def test_validator_accepts_single_category_batch():
    food_items = [item for item in make_valid_items() if item["type"] == "food"]

    result = AIResponseValidator().validate_response_schema(
        food_items, category="food"
    )

    assert len(result) == 15


def test_validator_rejects_wrong_type_in_category_batch():
    food_items = [item for item in make_valid_items() if item["type"] == "food"]
    food_items[0]["type"] = "shopping"

    with pytest.raises(RuntimeError):
        AIResponseValidator().validate_response_schema(
            food_items, category="food"
        )


def test_validator_keeps_first_15_when_ai_returns_extra():
    food_items = [item for item in make_valid_items() if item["type"] == "food"]
    extra = dict(food_items[0], name="food extra")

    result = AIResponseValidator().validate_response_schema(
        food_items + [extra], category="food"
    )

    assert len(result) == 15
    assert result == food_items


def test_validator_skips_incomplete_items_in_category_batch():
    food_items = [item for item in make_valid_items() if item["type"] == "food"]
    broken = dict(food_items[0], name="broken")
    del broken["environment"]

    result = AIResponseValidator().validate_response_schema(
        [broken] + food_items, category="food"
    )

    assert "broken" not in [item["name"] for item in result]
    assert len(result) == 15


def test_validator_rejects_too_few_in_category_batch():
    food_items = [item for item in make_valid_items() if item["type"] == "food"]

    with pytest.raises(RuntimeError):
        AIResponseValidator().validate_response_schema(
            food_items[:14], category="food"
        )


def test_validator_rejects_unknown_category():
    with pytest.raises(ValueError):
        AIResponseValidator().validate_response_schema(
            make_valid_items(), category="nightlife"
        )

@pytest.mark.parametrize(
    "cost",
    [-10, "unknown", None, float("inf"), float("-inf"), float("nan")]
)
def test_validator_rejects_invalid_cost_full_response(cost):
    items = make_valid_items()
    items[0]["estimated_cost_sgd"] = cost

    with pytest.raises(RuntimeError, match="invalid estimated_cost_sgd"):
        AIResponseValidator().validate_response_schema(items)


@pytest.mark.parametrize("cost", [0, 20.50, "15.50"])
def test_validator_accepts_valid_cost_full_response(cost):
    items = make_valid_items()
    items[0]["estimated_cost_sgd"] = cost

    result = AIResponseValidator().validate_response_schema(items)

    assert len(result) == 60


def test_validator_rejects_missing_cost_full_response():
    items = make_valid_items()
    del items[0]["estimated_cost_sgd"]

    with pytest.raises(RuntimeError, match="missing required fields"):
        AIResponseValidator().validate_response_schema(items)


@pytest.mark.parametrize(
    "cost",
    [-10, "unknown", None, float("inf"), float("nan")]
)
def test_validator_rejects_invalid_cost_single_category(cost):
    food_items = [
        item for item in make_valid_items()
        if item["type"] == "food"
    ]

    food_items[0]["estimated_cost_sgd"] = cost

    with pytest.raises(RuntimeError, match="invalid estimated_cost_sgd"):
        AIResponseValidator().validate_response_schema(
            food_items, category="food"
        )


@pytest.mark.parametrize("cost", [0, 20.50])
def test_validator_accepts_valid_cost_single_category(cost):
    food_items = [
        item for item in make_valid_items()
        if item["type"] == "food"
    ]

    food_items[0]["estimated_cost_sgd"] = cost

    result = AIResponseValidator().validate_response_schema(
        food_items, category="food"
    )

    assert len(result) == 15


def test_validator_rejects_missing_cost_single_category():
    food_items = [
        item for item in make_valid_items()
        if item["type"] == "food"
    ]

    del food_items[0]["estimated_cost_sgd"]

    with pytest.raises(RuntimeError, match="complete food recommendations"):
        AIResponseValidator().validate_response_schema(
            food_items, category="food"
        )