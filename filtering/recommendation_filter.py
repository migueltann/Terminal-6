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
        
    # checks 1 recommendation against every rule
    def evaluate(self, item: Recommendation) -> Recommendation:
        """Run every applicable rule and record the results on the item."""
        item.results = []  # clear any old results first
        for rule in self.rules:  # go through each rule one by one
            result = rule.check(item, self.requirements)  # run the rule
            if result is not None:  # None means the rule did not apply, so skip it
                item.results.append(result)  # save the pass/fail result on the item
        return item  # give back the item with its results
    
    # Gets the user's preferences for a recommendation category
    def _preferences(self, item_type: str) -> list[str]:
        return _active_preferences(self.requirements.preferences_for(item_type))

    # checks if the item costs half the budget or less
    def _within_half_budget(self, item: Recommendation) -> bool:
        return item.cost_sgd <= 0.5 * BudgetRule.limit_for(item, self.requirements)

    # checks if the item matches at least one of the user's preferences
    def _matches_preference(self, item: Recommendation) -> bool:
        item_data = item.to_dict()  # turn the item into a dict so we can search its text
        # any() is True if at least one preference is found in the item
        return any(_contains_term(item_data, pref) for pref in self._preferences(item.item_type))
