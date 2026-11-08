from logic_manager import _normalise  # lowercase, removes symbols and extra spaces
from models import Recommendation, RuleResult, UserRequirements  # the shared data classes
from .rule import Rule  # the parent class this rule is based on

class EnvironmentRule(Rule):
    """Checks whether the recommendation matches the user's environment preference."""
    label = "Environment"
    
# Checks whether the user selected an environment preference
    def applies_to(self, item: Recommendation, requirements: UserRequirements) -> bool:
        # accommodation has no environment requirement, so environment_for gives "Any"
        return self.is_set(requirements.environment_for(item.item_type))