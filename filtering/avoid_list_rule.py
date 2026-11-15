from .text_matcher import TextMatcher  # cleans the list and searches the item's text
from models import Recommendation, RuleResult, UserRequirements  # the shared data classes
from .rule import Rule  # the parent class this rule is based on

class AvoidListRule(Rule):
    """Checks whether the recommendation contains anything the user wants to avoid."""
    label = "Avoid list"  # name shown to the user
    
    # the actual avoid-list check
    def evaluate(self, item: Recommendation, requirements: UserRequirements) -> RuleResult:
        item_data = item.to_dict()  # Converts the recommendation into a dictionary
        
        matched = [term for term in TextMatcher.active_preferences(requirements.avoid_list) # Finds words from the avoid list that appear in the recommendation
                   if TextMatcher.contains_term(item_data, term)]
        
        # Passes if nothing from the avoid list is found.
        return self.result(
            not matched,
            "No avoided match",
            "Matched: " + ", ".join(matched)
        )