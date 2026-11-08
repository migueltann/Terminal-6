from dataclasses import dataclass

@dataclass
class RuleResult:
    label: str
    passed: bool
    detail: str

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "passed": self.passed,
            "detail": self.detail,
        }
    