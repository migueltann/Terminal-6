from dataclasses import dataclass, field

@dataclass
class UserRequirements:
    """The user's travel requirements, previously a plain dict."""
    destination: str
    budgets: dict[str, float | None] = field(default_factory=dict)
    preferences: dict[str, list[str]] = field(default_factory=dict)
    environments: dict[str, str] = field(default_factory=dict)
    dietary: str = "Any"
    transport: str = "Any"
    avoid_list: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "UserRequirements":
        if not isinstance(data, dict):
            raise TypeError("Requirements must be a dictionary")
        return cls(
            destination=str(data.get("destination", "")),
            budgets={key: data.get(key) for key in (
                "max_activity_spend", "max_meal_spend",
                "max_accommodation_spend", "max_shopping_spend")},
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
        return {
            "destination": self.destination,
            **self.budgets,
            **{key: list(value) for key, value in self.preferences.items()},
            **self.environments,
            "dietary": self.dietary,
            "preferred_transport": self.transport,
            "avoid_list": list(self.avoid_list),
        }

    def budget_for(self, item_type: str) -> float | None:
        key = {"activity": "max_activity_spend", "food": "max_meal_spend",
               "accommodation": "max_accommodation_spend", "shopping": "max_shopping_spend"}[item_type]
        return self.budgets.get(key)

    def preferences_for(self, item_type: str) -> list[str]:
        key = {"activity": "preferred_activities", "food": "food_preferences",
               "accommodation": "accommodation_preferences", "shopping": "shopping_preferences"}[item_type]
        return list(self.preferences.get(key, []))

    def environment_for(self, item_type: str) -> str:
        key = {"activity": "activity_environment", "food": "food_environment",
               "shopping": "shopping_environment"}.get(item_type)
        return self.environments.get(key, "Any") if key else "Any"
