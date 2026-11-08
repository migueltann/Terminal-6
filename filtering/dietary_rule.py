from logic_manager import _normalise  # Cleans text for comparison
from models import Recommendation, RuleResult, UserRequirements  # Shared data classes
from .rule import Rule  # Imports the parent class

# Creates a dietary rule using the parent Rule class
class DietaryRule(Rule):
    """Checks whether food matches the user's dietary needs."""
    label = "Dietary requirement"