from logic_manager import _normalise  # cleans text: lowercase, removes symbols and extra spaces
from models import Recommendation, RuleResult, UserRequirements  # the shared data classes
from .rule import Rule  # the parent class this rule is based on

# Creates a transport rule using the parent Rule class
class TransportRule(Rule):
    """Checks whether the recommendation supports the user's preferred transport."""
    label = "Transport preference"
    
    # only check this rule if the user picked a transport
    def applies_to(self, item: Recommendation, requirements: UserRequirements) -> bool:
        return self.is_set(requirements.transport)
    
    # the actual transport check
    def evaluate(self, item: Recommendation, requirements: UserRequirements) -> RuleResult:
         # Gets the user's preferred transport
        transport = _normalise(requirements.transport)