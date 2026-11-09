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
    
# ---------- EnvironmentRule ----------

# user wants outdoor activities, so an indoor activity should fail
def test_environment_mismatch_fails():
    item = make_item(environment="Indoor")
    result = EnvironmentRule().check(item, make_requirements())
    assert result.passed is False
    assert result.detail == "Indoor does not match Outdoor"


# hotels have no indoor/outdoor setting, so the rule should be skipped (None)
def test_environment_skipped_for_accommodation():
    item = make_item("accommodation", environment="Outdoor")
    assert EnvironmentRule().check(item, make_requirements()) is None


# if the user picked "Any", the rule should be skipped (None)
def test_environment_skipped_when_any():
    item = make_item(environment="Indoor")
    requirements = make_requirements(activity_environment="Any")
    assert EnvironmentRule().check(item, requirements) is None

# ---------- AvoidListRule ----------

# user wants to avoid museums, so "National Museum" should fail
def test_avoid_list_match_fails():
    item = make_item(name="National Museum")
    result = AvoidListRule().check(item, make_requirements(avoid_list=["museum"]))
    assert result.passed is False
    assert result.detail == "Matched: museum"  # message says which word matched


# "Night Safari" has nothing to do with museums, so it should pass
def test_avoid_list_no_match_passes():
    item = make_item(name="Night Safari")
    result = AvoidListRule().check(item, make_requirements(avoid_list=["museum"]))
    assert result.passed is True


# ---------- DietaryRule ----------

# user needs halal, but this food is only vegetarian, so it should fail
def test_dietary_mismatch_fails_for_food():
    item = make_item("food", dietary_tags=["vegetarian"])
    result = DietaryRule().check(item, make_requirements())
    assert result.passed is False
    assert result.detail == "halal not listed"


# the diet only matters for food, so it should be skipped for an activity (None)
def test_dietary_skipped_for_activities():
    item = make_item(dietary_tags=[])
    assert DietaryRule().check(item, make_requirements()) is None


# ---------- TransportRule ----------

# user wants transit, but this place can only be reached by taxi, so it should fail
def test_transport_mismatch_fails():
    item = make_item(transport_options=["taxi"])
    result = TransportRule().check(item, make_requirements())
    assert result.passed is False
    assert result.detail == "transit not listed"


# if the user picked "Any" transport, the rule should be skipped (None)
def test_transport_skipped_when_any():
    item = make_item(transport_options=["taxi"])
    requirements = make_requirements(preferred_transport="Any")
    assert TransportRule().check(item, requirements) is None

# ---------- RecommendationFilter ----------

# a good item should go to approved and an over-budget item should go to rejected
def test_filter_separates_approved_and_rejected():
    good = make_item(name="Good")
    bad = make_item(name="Too Expensive", estimated_cost_sgd=500)
    result = RecommendationFilter(make_requirements()).filter([good, bad])
    assert [item.name for item in result.approved()] == ["Good"]
    assert [item.name for item in result.rejected_items()] == ["Too Expensive"]


# after checking, the item should remember which rule it failed
def test_filter_records_failed_rule_on_item():
    item = make_item(estimated_cost_sgd=500)  # only breaks the budget
    RecommendationFilter(make_requirements()).evaluate(item)
    failed = [r.label for r in item.results if not r.passed]  # list the failed rules
    assert failed == ["Activity budget"]


# if we only give the filter the TransportRule, it should not check the budget
def test_filter_uses_only_the_rules_given():
    item = make_item(estimated_cost_sgd=500)  # over budget
    only_transport = RecommendationFilter(make_requirements(), rules=[TransportRule()])
    result = only_transport.filter([item])
    assert len(result.approved()) == 1  # budget rule was not used, so it is approved


# with preferences, a top pick must match a preference and cost half the budget or less
def test_top_pick_needs_preference_and_half_budget():
    requirements = make_requirements(preferred_activities=["hiking"])
    cheap_match = make_item(name="Hiking Trail", estimated_cost_sgd=20)  # matches + cheap = top pick
    pricey_match = make_item(name="Hiking Tour", estimated_cost_sgd=80)  # matches but over $50 = not
    cheap_no_match = make_item(name="Zoo", estimated_cost_sgd=10)  # cheap but not hiking = not
    RecommendationFilter(requirements).filter([cheap_match, pricey_match, cheap_no_match])
    assert cheap_match.is_top_pick() is True
    assert pricey_match.is_top_pick() is False
    assert cheap_no_match.is_top_pick() is False


# with no preferences, the 3 cheapest items within half the budget become top picks
def test_cheapest_three_are_top_picks_without_preferences():
    # makes 5 places costing $40, $10, $30, $20 and $60
    items = [make_item(name=f"Place {cost}", estimated_cost_sgd=cost)
             for cost in (40, 10, 30, 20, 60)]
    RecommendationFilter(make_requirements()).filter(items)
    picks = sorted(item.cost_sgd for item in items if item.is_top_pick())  # costs of the top picks
    assert picks == [10, 20, 30]  # 60 is over half the budget, 40 is 4th cheapest


# an item that failed a rule should never be a top pick, even if it is very cheap
def test_rejected_item_is_never_a_top_pick():
    item = make_item(estimated_cost_sgd=5, transport_options=["taxi"])  # cheap but wrong transport
    result = RecommendationFilter(make_requirements()).filter([item])
    assert item in result.rejected_items()
    assert item.is_top_pick() is False


# compares the old and new filtering methods to make sure they give the same results
def test_filter_gives_same_output_as_logic_manager():
    # 5 sample items: some pass, some fail
    raw_items = [
        make_item(name="Gardens", estimated_cost_sgd=10).to_dict(),  # passes
        make_item(name="Museum", environment="Indoor").to_dict(),  # fails environment
        make_item("food", name="Halal Cafe", estimated_cost_sgd=15).to_dict(),  # passes
        make_item("food", name="Steakhouse", estimated_cost_sgd=90).to_dict(),  # fails budget
        make_item("accommodation", name="Hotel", estimated_cost_sgd=150).to_dict(),  # passes
    ]
    # keep only the normal fields, like what the AI would send
    keep = ("name", "type", "category", "estimated_cost_sgd", "location",
            "environment", "description", "tags", "transport_options", "dietary_tags")
    raw_items = [{key: item[key] for key in keep} for item in raw_items]
    user_inputs = make_requirements().to_dict()  # the old functions use a plain dict

    # old logic_manager functions
    approved, rejected, _ = filter_recommendations([dict(i) for i in raw_items], user_inputs)
    old = build_processed_result("Singapore", user_inputs, approved, rejected)
