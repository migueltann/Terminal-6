"""UserRequirements: everything the user asked for when planning a trip."""
from dataclasses import dataclass, field

@dataclass
class UserRequirements:
    """The user's travel requirements, previously a plain dict."""
    destination: str
    # Max spend per type in SGD, e.g. {"max_meal_spend": 30.0}.
    # None means the user set no limit.
    budgets: dict[str, float | None] = field(default_factory=dict)
    # Liked keywords per type, e.g. {"food_preferences": ["ramen", "seafood"]}.
    preferences: dict[str, list[str]] = field(default_factory=dict)
    # "Indoor", "Outdoor" or "Any" per type, e.g. {"activity_environment": "Outdoor"}.
    environments: dict[str, str] = field(default_factory=dict)
    dietary: str = "Any"        # e.g. "Halal", "Vegetarian" or "Any"
    transport: str = "Any"      # preferred way to get around
    avoid_list: list[str] = field(default_factory=list)   # keywords to stay away from

    @classmethod
    def from_dict(cls, data: dict) -> "UserRequirements":
        """Build UserRequirements from the flat dict collected from the user.

        The input dict is flat (every key at the top level). Here the keys
        are grouped into budgets, preferences and environments.
        """
        if not isinstance(data, dict):
            raise TypeError("Requirements must be a dictionary")
        return cls(
            destination=str(data.get("destination", "")),
            budgets={key: data.get(key) for key in (
                "max_activity_spend", "max_meal_spend",
                "max_accommodation_spend", "max_shopping_spend")},
            # "or []" turns a missing or None value into an empty list.
            preferences={key: list(data.get(key) or []) for key in (
                "preferred_activities", "food_preferences",
                "accommodation_preferences", "shopping_preferences")},
            environments={key: str(data.get(key, "Any")) for key in (
                "activity_environment", "food_environment", "shopping_environment")},
            dietary=str(data.get("dietary", "Any")),
            transport=str(data.get("preferred_transport", "Any")),
            avoid_list=list(data.get("avoid_list") or []),
        )

    def to_dict(self) -> dict:
        """Flatten back into the original dict format (reverse of from_dict)."""
        return {
            "destination": self.destination,
            # "**" spreads each grouped dict's keys into this one flat dict.
            **self.budgets,
            **{key: list(value) for key, value in self.preferences.items()},
            **self.environments,
            "dietary": self.dietary,
            "preferred_transport": self.transport,
            "avoid_list": list(self.avoid_list),
        }

    def budget_for(self, item_type: str) -> float | None:
        """Return the max spend for one type ("activity", "food", ...), or None."""
        # Map the recommendation type to the key its budget is stored under.
        key = {"activity": "max_activity_spend", "food": "max_meal_spend",
               "accommodation": "max_accommodation_spend", "shopping": "max_shopping_spend"}[item_type]
        return self.budgets.get(key)

    def preferences_for(self, item_type: str) -> list[str]:
        """Return the user's liked keywords for one type."""
        key = {"activity": "preferred_activities", "food": "food_preferences",
               "accommodation": "accommodation_preferences", "shopping": "shopping_preferences"}[item_type]
        return list(self.preferences.get(key, []))

    def environment_for(self, item_type: str) -> str:
        """Return "Indoor", "Outdoor" or "Any" for one type.

        Accommodation has no environment setting, so it is always "Any".
        """
        key = {"activity": "activity_environment", "food": "food_environment",
               "shopping": "shopping_environment"}.get(item_type)
        return self.environments.get(key, "Any") if key else "Any"
