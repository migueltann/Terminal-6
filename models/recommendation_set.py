from dataclasses import dataclass, field
from .user_requirements import UserRequirements
from .recommendation import Recommendation

@dataclass
class RecommendationSet:
    destination: str
    requirements: UserRequirements
    items: list[Recommendation] = field(default_factory=list)
    rejected: list[Recommendation] = field(default_factory=list)

    def add_item(self, item: Recommendation) -> None:
        self.items.append(item)

    def add_rejected(self, item: Recommendation) -> None:
        self.rejected.append(item)

    def approved(self) -> list[Recommendation]:
        return list(self.items)

    def rejected_items(self) -> list[Recommendation]:
        return list(self.rejected)

    def by_category(self) -> dict[str, list[Recommendation]]:
        return {category: [item for item in self.items if item.item_type == item_type]
                for category, item_type in (("activities", "activity"), ("food", "food"),
                                            ("accommodation", "accommodation"),
                                            ("shopping", "shopping"))}

    def summary(self) -> dict[str, int]:
        return {"approved_count": len(self.items), "filtered_out_count": len(self.rejected)}

    def to_dict(self) -> dict:
        grouped = self.by_category()
        return {"destination": self.destination,
                "requirements": self.requirements.to_dict(),
                "summary": self.summary(),
                **{key: [item.to_dict() for item in values] for key, values in grouped.items()},
                "filtered_out": [item.to_dict() for item in self.rejected]}

    @classmethod
    def from_dict(cls, data: dict) -> "RecommendationSet":
        if not isinstance(data, dict):
            raise TypeError("Saved result must be a dictionary")

        destination = str(data["destination"])

        requirements_data = dict(data.get("requirements") or {})
        requirements_data.setdefault("destination", destination)

        result = cls(
            destination=destination,
            requirements=UserRequirements.from_dict(requirements_data),
            )

        for category in ("activities", "food", "accommodation", "shopping"):

            for item_data in data.get(category) or []:
                result.add_item(Recommendation.from_dict(item_data))

        for item_data in data.get("filtered_out") or []:
            result.add_rejected(
                Recommendation.from_dict(item_data))
        
        return result
