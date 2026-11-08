from logic_manager import _normalise  # Cleans text for comparison
from models import Recommendation, RuleResult, UserRequirements  # Shared data classes
from .rule import Rule  # Imports the parent class

# Creates a dietary rule using the parent Rule class
class DietaryRule(Rule):
    """Checks whether food matches the user's dietary needs."""
    label = "Dietary requirement"
    
    # Only checks food items when the user has selected a diet.
    def applies_to(self, item: Recommendation, requirements: UserRequirements) -> bool:
        """Checks whether the dietary rule should be used."""
        return item.item_type == "food" and self.is_set(requirements.dietary)

    # Checks whether the food meets the user's diet.
    def evaluate(self, item: Recommendation, requirements: UserRequirements) -> RuleResult:
        # Cleans the user's dietary requirement.
        dietary = _normalise(requirements.dietary)
        
        # pass if the diet is in the item's dietary tags
        return self.result(
            dietary in item.dietary_tags,
                f"{dietary} supported", # pass messages
                f"{dietary} not listed" # fail messages
        )  