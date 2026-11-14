"""RecommendationSet: one saved trip's results after filtering.

It holds the destination, the user's requirements, the recommendations
that passed every rule (items) and the ones that failed (rejected).
This is the object that gets saved to and loaded from the data folder.
"""
from dataclasses import dataclass, field
from .user_requirements import UserRequirements
from .recommendation import Recommendation

@dataclass
class RecommendationSet:
    """All recommendations for one destination, split into approved and rejected."""
    destination: str
    requirements: UserRequirements
    # field(default_factory=list) gives each new set its own empty list.
    # (Writing "= []" would make every set share the same list.)
    items: list[Recommendation] = field(default_factory=list)     # passed every rule
    rejected: list[Recommendation] = field(default_factory=list)  # failed at least one rule

    def add_item(self, item: Recommendation) -> None:
        """Add a recommendation that passed the filters."""
        self.items.append(item)

    def add_rejected(self, item: Recommendation) -> None:
        """Add a recommendation that was filtered out."""
        self.rejected.append(item)

    def approved(self) -> list[Recommendation]:
        """Return a copy of the approved list, so callers cannot change ours."""
        return list(self.items)

    def rejected_items(self) -> list[Recommendation]:
        """Return a copy of the rejected list."""
        return list(self.rejected)

    def by_category(self) -> dict[str, list[Recommendation]]:
        """Group approved items by type, e.g. {"activities": [...], "food": [...]}.

        The keys are the plural names used in the saved JSON file, while
        each Recommendation stores the singular type ("activity").
        """
        return {category: [item for item in self.items if item.item_type == item_type]
                for category, item_type in (("activities", "activity"), ("food", "food"),
                                            ("accommodation", "accommodation"),
                                            ("shopping", "shopping"))}

    def summary(self) -> dict[str, int]:
        """Count how many recommendations were kept and how many were removed."""
        return {"approved_count": len(self.items), "filtered_out_count": len(self.rejected)}

    def to_dict(self) -> dict:
        """Convert the whole set into plain dicts/lists so it can be saved as JSON."""
        grouped = self.by_category()
        return {"destination": self.destination,
                "requirements": self.requirements.to_dict(),
                "summary": self.summary(),
                # "**" unpacks the grouped dict here, adding one key per
                # category: "activities", "food", "accommodation", "shopping".
                **{key: [item.to_dict() for item in values] for key, values in grouped.items()},
                "filtered_out": [item.to_dict() for item in self.rejected]}

    @classmethod
    def from_dict(cls, data: dict) -> "RecommendationSet":
        """Rebuild a RecommendationSet from a dict loaded from a JSON file.

        This is the reverse of to_dict().
        """
        if not isinstance(data, dict):
            raise TypeError("Saved result must be a dictionary")

        destination = str(data["destination"])

        # Older saved files may not store the destination inside
        # "requirements", so fill it in from the top level if missing.
        requirements_data = dict(data.get("requirements") or {})
        requirements_data.setdefault("destination", destination)

        result = cls(
            destination=destination,
            requirements=UserRequirements.from_dict(requirements_data),
            )

        # Put the approved items from every category back into one list.
        # "or []" handles a category that is missing or null in the file.
        for category in ("activities", "food", "accommodation", "shopping"):

            for item_data in data.get(category) or []:
                result.add_item(Recommendation.from_dict(item_data))

        for item_data in data.get("filtered_out") or []:
            result.add_rejected(
                Recommendation.from_dict(item_data))

        return result
