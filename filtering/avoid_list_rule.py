from logic_manager import _active_preferences, _contains_term  # helpers that clean the list and search the item's text
from models import Recommendation, RuleResult, UserRequirements  # the shared data classes
from .rule import Rule  # the parent class this rule is based on

class AvoidListRule(Rule):
    """Checks whether the recommendation contains anything the user wants to avoid."""
    label = "Avoid list"  # name shown to the user