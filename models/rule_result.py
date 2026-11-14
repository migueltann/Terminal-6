"""RuleResult: the outcome of checking one recommendation against one rule."""
from dataclasses import dataclass

@dataclass
class RuleResult:
    """Whether a recommendation passed a single filtering rule, and why.

    Example: RuleResult("Budget", False, "Costs SGD 80, over your SGD 50 limit")
    """
    label: str      # name of the rule, e.g. "Budget" or "Dietary"
    passed: bool    # True if the recommendation satisfied this rule
    detail: str     # human-readable explanation shown to the user

    def to_dict(self) -> dict:
        """Convert to a plain dict so it can be saved as JSON."""
        return {
            "label": self.label,
            "passed": self.passed,
            "detail": self.detail,
        }
