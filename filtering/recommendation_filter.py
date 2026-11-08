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
    
    # selects the best recommendations from each category
    def _mark_top_picks(self, approved: list[Recommendation]) -> None:

        # goes through each recommendation category
        for item_type in ("activity", "food", "accommodation", "shopping"):

            #gets recommendations belonging to this category
            in_category = [
                item for item in approved
                if item.item_type == item_type
            ]
            
            # checks whether the user has preferences for this category
            if self._preferences(item_type):

                # selects affordable recommendations that match the user's preferences
                for item in in_category:
                    if self._within_half_budget(item) and self._matches_preference(item):
                        item.mark_top_pick(PREFERENCE_REASON)
            else:
                # Gets affordable recommendations and sorts them by price.
                affordable = sorted(
                    (item for item in in_category if self._within_half_budget(item)),
                    key=lambda item: item.cost_sgd
                )
                for item in affordable[:CHEAPEST_TOP_PICK_COUNT]:  # take only the cheapest few (3)
                    item.mark_top_pick(CHEAPEST_REASON)  # mark it as a top pick and save the reason

    # filters all recommendations and returns the final results
    def filter(self, items: list[Recommendation], destination: Optional[str] = None) -> RecommendationSet:
        """Separates approved and rejected recommendations and selects top picks."""

        # creates an empty result set using the given destination or the user's destination
        result = RecommendationSet(
            destination or self.requirements.destination,
            self.requirements
        )
        
        # checks each recommendation using all the rules
        for item in items:
            self.evaluate(item)
            
            # add the recommendation to the approved or rejected list
            if item.is_eligible():
                result.add_item(item)
            else:
                result.add_rejected(item)
            
        # select top picks from approved recommendations only
        self._mark_top_picks(result.approved())

        # returns the final recommendation results
        return result