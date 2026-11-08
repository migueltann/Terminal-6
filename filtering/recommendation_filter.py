from typing import Optional  
from logic_manager import CHEAPEST_TOP_PICK_COUNT, _active_preferences, _contains_term  # shared settings and helpers
from models import Recommendation, RecommendationSet, UserRequirements  # the shared data classes
from .rule import Rule  # the parent class of all rules
from .budget_rule import BudgetRule  # each of the 5 rules
from .environment_rule import EnvironmentRule
from .avoid_list_rule import AvoidListRule
from .dietary_rule import DietaryRule
from .transport_rule import TransportRule

# reasons shown to the user when an item is marked as a top pick
PREFERENCE_REASON = "matches your preferences and costs no more than half of your budget"
CHEAPEST_REASON = "one of the cheapest options and within half of your budget"

# this class runs all the rules on every recommendation
class RecommendationFilter:
    """Applies every rule to each recommendation and builds a RecommendationSet."""
    
     # Runs when a RecommendationFilter object is created
    def __init__(self, requirements: UserRequirements, rules: Optional[list[Rule]] = None):
        self.requirements = requirements  # save the user's requirements
        # use the rules given, or if none were given, use all 5 rules by default
        self.rules = rules if rules is not None else [
            BudgetRule(), EnvironmentRule(), AvoidListRule(), DietaryRule(), TransportRule(),
        ]
