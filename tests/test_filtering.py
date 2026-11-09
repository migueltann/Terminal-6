import pytest 

from logic_manager import filter_recommendations, build_processed_result  # the old functions, used to compare
from models import Recommendation, UserRequirements  # the shared data classes
from filtering import (  # all my classes from the filtering package
    Rule,
    BudgetRule,
    EnvironmentRule,
    AvoidListRule,
    DietaryRule,
    TransportRule,
    RecommendationFilter,
)

# Creates the default requirements for testing
def make_requirements(**changes):
    data = {
        "destination": "Singapore",
        "max_activity_spend": 100,  # activity budget is $100
        "max_meal_spend": 40,  # meal budget is $40
        "max_accommodation_spend": 200,  # hotel budget is $200
        "max_shopping_spend": 80,  # shopping budget is $80
        "activity_environment": "Outdoor",  # user wants outdoor activities
        "food_environment": "Indoor",  # user wants indoor food places
        "shopping_environment": "Indoor",  # user wants indoor shopping
        "dietary": "halal",  # user needs halal food
        "preferred_transport": "transit",  # user wants to take public transport
        "avoid_list": [],  # nothing to avoid by default
    }
    data.update(changes)  # replace any values the test wants to change
    return UserRequirements.from_dict(data)  # turn the dict into a UserRequirements object

# Creates a sample recommendation for testing
def make_item(item_type="activity", **changes):
    data = {
        "name": "Test Recommendation",
        "type": item_type,  # activity, food, accommodation or shopping
        "category": "General",
        "estimated_cost_sgd": 30,  # $30, which is within every budget above
        "location": "Singapore",
        # activities are outdoor and everything else is indoor, to match the user above
        "environment": "Outdoor" if item_type == "activity" else "Indoor",
        "description": "A sample recommendation",
        "tags": [],
        "transport_options": ["transit", "walk"],  # can be reached by transit
        "dietary_tags": ["halal"],  # serves halal food
    }
    data.update(changes)  # replace any values the test wants to change
    return Recommendation.from_dict(data)  # turn the dict into a Recommendation object

# ---------- Rule (abstract class) ----------

# Checks that Rule cannot be created directly because it is an abstract class
def test_rule_cannot_be_created_directly():
    with pytest.raises(TypeError):  # this test passes only if a TypeError happens
        Rule()

# ---------- BudgetRule ----------

# a $30 activity with a $100 budget should pass
def test_budget_within_limit_passes():
    result = BudgetRule().check(make_item(), make_requirements())
    assert result.passed is True
    assert result.label == "Activity budget"  # label changes based on the item type
    assert result.detail == "$30.00 <= $100.00"  # message shows both amounts


# a $50 meal with a $40 meal budget should fail
def test_budget_over_limit_fails():
    item = make_item("food", estimated_cost_sgd=50)
    result = BudgetRule().check(item, make_requirements())
    assert result.passed is False
    assert result.label == "Meal budget"
    assert result.detail == "$50.00 > $40.00"


# if the user left the budget empty, even a $9999 item should pass
def test_budget_missing_means_no_limit():
    item = make_item(estimated_cost_sgd=9999)
    result = BudgetRule().check(item, make_requirements(max_activity_spend=None))
    assert result.passed is True
    assert result.detail == "No budget limit set"