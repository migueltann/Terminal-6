from abc import ABC, abstractmethod  # create  abstract  class
from typing import Optional 
from logic_manager import _normalise  # lowercase, removes symbols and extra spaces
from models import Recommendation, RuleResult, UserRequirements  # the shared data classes

# answers if user did not pick anything
NO_REQUIREMENT = {"", "any", "none"}

class Rule(ABC):
    """A parent class for all recommendation rules."""
    label = "Rule"  
    
    # Checks whether this rule applies to the recommendation.
    def applies_to(self, item: Recommendation, requirements: UserRequirements) -> bool:
        """Checks whether this rule should be used."""
        return True

    @abstractmethod
    def evaluate(self, item: Recommendation, requirements: UserRequirements) -> RuleResult:
        """Checks the recommendation and explains whether it passes or fails."""

    # Runs the rule to check one recommendation.
    def check(self, item: Recommendation, requirements: UserRequirements) -> Optional[RuleResult]:
        """Checks the recommendation or skips it if the rule does not apply."""

        if not self.applies_to(item, requirements):  # Check if this rule applies.
            return None  # Skip the rule if it does not apply.

        return self.evaluate(item, requirements)  # Check if the recommendation passes or fails.
    
    # Creates a result in the same format for every rule.
    def result(self, passed: bool, pass_text: str, fail_text: str, label: Optional[str] = None) -> RuleResult:
        """Creates a result showing whether the recommendation passed or failed."""
        return RuleResult(label or self.label, passed, pass_text if passed else fail_text)

    # Checks whether the user has selected a requirement.
    @staticmethod  # Does not need self because it does not use the rule's data.
    def is_set(value) -> bool:
        """Checks whether the user entered a requirement."""

        # Removes extra spaces and checks that the value is not empty, Any or None.
        return _normalise(value) not in NO_REQUIREMENT
