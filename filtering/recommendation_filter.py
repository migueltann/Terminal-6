from typing import Optional  
from logic_manager import CHEAPEST_TOP_PICK_COUNT, _active_preferences, _contains_term  # shared settings and helpers
from models import Recommendation, RecommendationSet, UserRequirements  # the shared data classes
from .rule import Rule  # the parent class of all rules
from .budget_rule import BudgetRule  # each of the 5 rules
from .environment_rule import EnvironmentRule
from .avoid_list_rule import AvoidListRule
from .dietary_rule import DietaryRule
from .transport_rule import TransportRule