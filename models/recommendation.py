"""Recommendation: one place suggested by the AI (an activity, food, hotel or shop)."""
from dataclasses import dataclass, field
from typing import Any, ClassVar
from .rule_result import RuleResult

@dataclass
class Recommendation:
    """Represents one AI recommendation, including its filtering results."""
    name: str
    item_type: str          # "activity", "food", "accommodation" or "shopping"
    category: str           # finer label from the AI, e.g. "Museum" or "Hostel"
    cost_sgd: float
    location: str
    environment: str        # "Indoor" or "Outdoor"
    description: str
    tags: list[str] = field(default_factory=list)                # keywords used for matching
    transport_options: list[str] = field(default_factory=list)   # "walk", "transit", "taxi"
    dietary_tags: list[str] = field(default_factory=list)        # e.g. "halal", "vegetarian"
    shopping_types: list[str] = field(default_factory=list)      # e.g. "mall", "street_market"
    shopping_interests: list[str] = field(default_factory=list)  # e.g. "fashion", "souvenirs"
    results: list[RuleResult] = field(default_factory=list)      # one result per filtering rule
    top_pick: bool = False
    top_pick_reason: str = ""
    # Any extra keys from the AI that are not listed above, kept so
    # nothing is lost when the recommendation is saved again.
    extra: dict[str, Any] = field(default_factory=dict)
    best_time: str = "any"      # morning, afternoon, evening or any (from the AI)

    # Times of day the AI may give. Anything else becomes "any".
    # ClassVar means this belongs to the class, not to each object,
    # so the dataclass does not treat it as a field.
    BEST_TIMES: ClassVar[tuple[str, ...]] = ("morning", "afternoon", "evening", "any")

    def __post_init__(self) -> None:
        """Runs automatically after the dataclass __init__ sets the fields."""
        self.best_time = self.clean_best_time(self.best_time)

    @classmethod
    def clean_best_time(cls, value: Any) -> str:
        """Lower-case the AI's answer, and use "any" if it is missing or unknown."""
        text = str(value or "").strip().lower()
        return text if text in cls.BEST_TIMES else "any"

    @classmethod
    def from_dict(cls, data: dict) -> "Recommendation":
        """Build a Recommendation from a dict (from the AI or a saved JSON file)."""
        if not isinstance(data, dict):
            raise TypeError("Recommendation must be a dictionary")
        # Keys that map to a field above. Every other key goes into "extra".
        standard = {"name", "type", "category", "estimated_cost_sgd", "location",
                    "environment", "description", "tags", "transport_options",
                    "dietary_tags", "shopping_types", "shopping_interests",
                    "checks", "eligible", "top_pick", "top_pick_reason",
                    "passed_rules", "failed_rules", "best_time"}
        # Required keys use data["..."] (a KeyError if missing); optional
        # ones use data.get(...) with a default.
        return cls(
            name=str(data["name"]), item_type=str(data["type"]),
            category=str(data["category"]), cost_sgd=float(data["estimated_cost_sgd"]),
            location=str(data["location"]), environment=str(data["environment"]),
            description=str(data["description"]),
            tags=list(data.get("tags") or []),
            transport_options=list(data.get("transport_options") or []),
            dietary_tags=list(data.get("dietary_tags") or []),
            shopping_types=list(data.get("shopping_types") or []),
            shopping_interests=list(data.get("shopping_interests") or []),
            # Saved files store rule results under "checks"; "**x" passes
            # each dict's keys as RuleResult(label=..., passed=..., detail=...).
            results=[RuleResult(**x) for x in data.get("checks", [])],
            top_pick=bool(data.get("top_pick", False)),
            top_pick_reason=str(data.get("top_pick_reason") or ""),
            extra={k: v for k, v in data.items() if k not in standard},
            best_time=data.get("best_time"),     # older saved sets have none -> "any"
        )

    def is_eligible(self) -> bool:
        """True only if the recommendation passed every rule."""
        return all(result.passed for result in self.results)

    def mark_top_pick(self, reason: str) -> None:
        """Highlight this recommendation as a top pick, with the reason why."""
        self.top_pick = True
        self.top_pick_reason = reason

    def is_top_pick(self) -> bool:
        return self.top_pick

    def to_dict(self) -> dict:
        """Convert to a plain dict for saving as JSON or showing on the web page."""
        # "extra" goes first so the standard fields below win if a key
        # appears in both.
        result = {**self.extra, "name": self.name, "type": self.item_type,
                  "category": self.category, "estimated_cost_sgd": self.cost_sgd,
                  "location": self.location, "environment": self.environment,
                  "description": self.description, "best_time": self.best_time,
                  "tags": list(self.tags),
                  "transport_options": list(self.transport_options),
                  "dietary_tags": list(self.dietary_tags), "eligible": self.is_eligible(),
                  "top_pick": self.top_pick, "checks": [r.to_dict() for r in self.results],
                  # Rule names split by outcome, for easy display.
                  "passed_rules": [r.label for r in self.results if r.passed],
                  "failed_rules": [r.label for r in self.results if not r.passed]}
        # Shopping fields are only included when they are relevant.
        if self.item_type == "shopping" or self.shopping_types or self.shopping_interests:
            result["shopping_types"] = list(self.shopping_types)
            result["shopping_interests"] = list(self.shopping_interests)
        if self.top_pick_reason:
            result["top_pick_reason"] = self.top_pick_reason
        return result