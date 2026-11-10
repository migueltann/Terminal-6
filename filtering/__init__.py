"""public import"""

from .rule import Rule  # the parent class that every rule is based on
from .budget_rule import BudgetRule  # checks if the item is within budget
from .environment_rule import EnvironmentRule  # checks indoor / outdoor
from .avoid_list_rule import AvoidListRule  # checks the item has nothing the user wants to avoid
from .dietary_rule import DietaryRule  # checks food matches the user's diet (e.g. halal)
from .transport_rule import TransportRule  # checks the user's preferred transport can reach it
from .recommendation_filter import RecommendationFilter  # runs all the rules together
from .logic_manager import LogicManager  # the Logic Manager that uses the filter

# list of names that are shared when someone writes "from filtering import *"
__all__ = ["Rule", "BudgetRule", "EnvironmentRule", "AvoidListRule",
           "DietaryRule", "TransportRule", "RecommendationFilter", "LogicManager"]
