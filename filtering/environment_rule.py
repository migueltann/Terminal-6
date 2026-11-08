from logic_manager import _normalise  # lowercase, removes symbols and extra spaces
from models import Recommendation, RuleResult, UserRequirements  # the shared data classes
from .rule import Rule  # the parent class this rule is based on

class EnvironmentRule(Rule):
    """Checks whether the recommendation matches the user's environment preference."""
    label = "Environment"