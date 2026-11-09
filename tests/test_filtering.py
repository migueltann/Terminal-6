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

# Creates a sample recommendation for testing
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
