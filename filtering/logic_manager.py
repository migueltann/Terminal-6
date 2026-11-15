"""Logic Manager: applies the Python rules to the AI's recommendations."""

from typing import Optional

from models import Recommendation, RecommendationSet, UserRequirements
from .rule import Rule
from .recommendation_filter import RecommendationFilter


class LogicManager:
    """Checks every AI recommendation against the user's requirements.

    It never calls the AI, reads files or prints: it only receives objects
    from the other managers and returns a RecommendationSet.
    """

    def __init__(self) -> None:
        # Composition: the LogicManager creates and owns its filter.
        # It is made in process(), because the filter needs that request's requirements.
        # The double underscore makes it private (encapsulation), so code
        # outside this class cannot reach it as manager.__filter.
        self.__filter: Optional[RecommendationFilter] = None

    @staticmethod
    def _default_rules() -> list[Rule]:
        """Fresh copies of the five filtering rules (defined once in RecommendationFilter)."""
        return RecommendationFilter.default_rules()

    def _check_inputs(self, reqs: UserRequirements, items: list[Recommendation]) -> None:
        """Stop early with a clear error if the inputs are the wrong type."""
        if not isinstance(reqs, UserRequirements):
            raise TypeError("reqs must be a UserRequirements object")
        if not isinstance(items, list):
            raise TypeError("items must be a list of Recommendation objects")
        for item in items:
            if not isinstance(item, Recommendation):
                raise TypeError("every item must be a Recommendation object")

    def process(self, reqs: UserRequirements, items: list[Recommendation]) -> RecommendationSet:
        """Run every rule on every item and return approved and rejected items.

        A new RecommendationFilter is made for each request because the filter
        needs this request's requirements. Fresh rule objects are passed into it
        (aggregation), and top picks are marked inside the filter.
        """
        self._check_inputs(reqs, items)
        self.__filter = RecommendationFilter(reqs, self._default_rules())
        return self.__filter.filter(items, reqs.destination)