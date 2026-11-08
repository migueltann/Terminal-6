import math  
from models import Recommendation, RuleResult, UserRequirements  # the shared data classes
from .rule import Rule  # the parent class this rule is based on

# Stores the budget name for each recommendation type
BUDGET_LABELS = {
    "activity": "Activity budget",
    "food": "Meal budget",
    "accommodation": "Accommodation budget",
    "shopping": "Shopping budget",
}

class BudgetRule(Rule):
    """Checks whether the item's cost is within the user's budget."""
    label = "Budget"