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
    
    # finds the user's budget for this item's category 
    @staticmethod  # static so the RecommendationFilter can also use it for top picks
    def limit_for(item: Recommendation, requirements: UserRequirements) -> float:
        """Gets the budget limit or returns infinity if it is invalid."""
        try:
            # Gets the budget and converts it into a number.
            limit = float(requirements.budget_for(item.item_type))
        except (TypeError, ValueError):  # budget is empty or not a number
            return math.inf  # treat it as no spending limit
        # returns infinity if the budget is invalid or negative
        return math.inf if math.isnan(limit) or limit < 0 else limit

    # Checks whether the recommendation is within the user's budget
    def evaluate(self, item: Recommendation, requirements: UserRequirements) -> RuleResult:
        # Gets the item's cost and the user's budget
        cost = item.cost_sgd 
        limit = self.limit_for(item, requirements) 
        
        # Creates the message to show when the recommendation passes
        pass_text = (
            "No budget limit set" if math.isinf(limit)
            else f"${cost:.2f} <= ${limit:.2f}"
        )
        
        # Checks whether the cost is within the budget
        return self.result(
            cost <= limit,
            pass_text,
            f"${cost:.2f} > ${limit:.2f}",
            label=BUDGET_LABELS.get(item.item_type, self.label)
        )
