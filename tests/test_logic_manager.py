
from logic_manager import (
    evaluate_recommendation,
    filter_recommendations,
    validate_ai_response,
    build_processed_result,
)


def make_requirements():
    return {
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


def make_item(item_type="activity", **changes):
    item = {
        "name": "Test Recommendation",
        "type": item_type,
        "category": "General",
        "estimated_cost_sgd": 30,
        "location": "Singapore",
        "environment": (
            "Outdoor" if item_type == "activity" else "Indoor"
        ),
        "description": "A sample recommendation",
        "tags": [],
        "transport_options": ["transit", "walk"],
        "dietary_tags": ["halal"],
    }

    if item_type == "shopping":
        item["shopping_types"] = []
        item["shopping_interests"] = []

    item.update(changes)
    return item


def test_valid_activity_passes():
    decision = evaluate_recommendation(
        make_item(), make_requirements()
    )
    assert decision["keep"] is True
    assert decision["failed_rules"] == []


def test_activity_over_budget_fails():
    item = make_item(estimated_cost_sgd=150)
    decision = evaluate_recommendation(item, make_requirements())
    assert decision["keep"] is False
    assert "Activity budget" in decision["failed_rules"]


def test_food_over_budget_fails():
    item = make_item("food", estimated_cost_sgd=50)
    decision = evaluate_recommendation(item, make_requirements())
    assert decision["keep"] is False
    assert "Meal budget" in decision["failed_rules"]


def test_accommodation_over_budget_fails():
    item = make_item("accommodation", estimated_cost_sgd=250)
    decision = evaluate_recommendation(item, make_requirements())
    assert decision["keep"] is False
    assert "Accommodation budget" in decision["failed_rules"]


def test_shopping_over_budget_fails():
    item = make_item("shopping", estimated_cost_sgd=90)
    decision = evaluate_recommendation(item, make_requirements())
    assert decision["keep"] is False
    assert "Shopping budget" in decision["failed_rules"]


def test_activity_environment_mismatch_fails():
    item = make_item(environment="Indoor")
    decision = evaluate_recommendation(item, make_requirements())
    assert decision["keep"] is False
    assert "Environment" in decision["failed_rules"]


def test_food_environment_mismatch_fails():
    item = make_item("food", environment="Outdoor")
    decision = evaluate_recommendation(item, make_requirements())
    assert decision["keep"] is False
    assert "Environment" in decision["failed_rules"]


def test_shopping_environment_mismatch_fails():
    item = make_item("shopping", environment="Outdoor")
    decision = evaluate_recommendation(item, make_requirements())
    assert decision["keep"] is False
    assert "Environment" in decision["failed_rules"]


def test_accommodation_has_no_environment_restriction():
    item = make_item("accommodation", environment="Outdoor")
    decision = evaluate_recommendation(item, make_requirements())
    assert decision["keep"] is True
    assert "Environment" not in [
        check["label"] for check in decision["checks"]
    ]


def test_food_dietary_mismatch_fails():
    item = make_item("food", dietary_tags=["vegetarian"])
    decision = evaluate_recommendation(item, make_requirements())
    assert decision["keep"] is False
    assert "Dietary requirement" in decision["failed_rules"]


def test_dietary_does_not_restrict_activities():
    item = make_item("activity", dietary_tags=[])
    decision = evaluate_recommendation(item, make_requirements())
    assert decision["keep"] is True


def test_transport_mismatch_fails():
    item = make_item(transport_options=["taxi"])
    decision = evaluate_recommendation(item, make_requirements())
    assert decision["keep"] is False
    assert "Transport preference" in decision["failed_rules"]


def test_avoid_list_fails_on_matching_name():
    requirements = make_requirements()
    requirements["avoid_list"] = ["nightlife"]

    item = make_item(name="Nightlife Tour")
    decision = evaluate_recommendation(item, requirements)

    assert decision["keep"] is False
    assert "Avoid list" in decision["failed_rules"]


def test_any_transport_skips_transport_restriction():
    requirements = make_requirements()
    requirements["preferred_transport"] = "Any"

    item = make_item(transport_options=[])
    decision = evaluate_recommendation(item, requirements)

    assert decision["keep"] is True


def test_filter_separates_approved_and_rejected():
    items = [
        make_item(name="Affordable Activity"),
        make_item(
            name="Expensive Activity",
            estimated_cost_sgd=150,
        ),
    ]

    approved, rejected, audit = filter_recommendations(
        items, make_requirements()
    )

    assert len(approved) == 1
    assert len(rejected) == 1
    assert len(audit) == 2
    assert approved[0]["eligible"] is True
    assert rejected[0]["eligible"] is False
    assert "Activity budget" in rejected[0]["failed_rules"]


def test_processed_result_groups_categories():
    items = [
        make_item("activity"),
        make_item("food"),
        make_item("accommodation"),
        make_item("shopping"),
    ]

    requirements = make_requirements()

    approved, rejected, _ = filter_recommendations(
        items, requirements
    )

    result = build_processed_result(
        "Singapore", requirements, approved, rejected
    )

    assert len(result["activities"]) == 1
    assert len(result["food"]) == 1
    assert len(result["accommodation"]) == 1
    assert len(result["shopping"]) == 1
    assert result["summary"]["approved_count"] == 4


def test_validation_rejects_missing_environment():
    item = make_item()
    del item["environment"]

    assert validate_ai_response([item]) == []


def test_validation_accepts_complete_item():
    item = make_item()

    validated = validate_ai_response([item])

    assert len(validated) == 1
    assert validated[0]["type"] == "activity"

def test_top_pick_needs_preference_and_low_cost():
    requirements = make_requirements()
    requirements["preferred_activities"] = ["museum"]

    cheap = make_item(name="City Museum", estimated_cost_sgd=20)
    pricey = make_item(name="City Museum", estimated_cost_sgd=80)
    unrelated = make_item(name="Harbour Cruise", estimated_cost_sgd=20)

    assert evaluate_recommendation(cheap, requirements)["top_pick"] is True
    assert evaluate_recommendation(pricey, requirements)["top_pick"] is False
    assert evaluate_recommendation(unrelated, requirements)["top_pick"] is False


def test_rejected_item_is_never_a_top_pick():
    requirements = make_requirements()
    requirements["preferred_activities"] = ["museum"]

    item = make_item(name="City Museum", estimated_cost_sgd=500)
    decision = evaluate_recommendation(item, requirements)

    assert decision["keep"] is False
    assert decision["top_pick"] is False


def test_hardcoded_ai_response_goes_through_the_whole_pipeline():
    """Sample AI output (one valid, one malformed) -> validate -> filter."""
    sample_ai_response = [
        {
            "name": "Gardens by the Bay",
            "type": "activity",
            "category": "Nature",
            "estimated_cost_sgd": 28,
            "location": "Marina Bay",
            "environment": "Outdoor",
            "description": "Large waterfront garden complex",
            "tags": ["nature", "gardens"],
            "transport_options": ["transit", "walk"],
            "dietary_tags": ["none"],
        },
        {"name": "Broken record", "type": "activity"},
    ]

    valid = validate_ai_response(sample_ai_response)
    assert len(valid) == 1

    approved, rejected, _ = filter_recommendations(valid, make_requirements())
    assert [item["name"] for item in approved] == ["Gardens by the Bay"]
    assert rejected == []
