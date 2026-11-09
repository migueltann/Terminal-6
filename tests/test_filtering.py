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