from dataclasses import dataclass


@dataclass
class GuardrailResult:
    allowed: bool
    reasons: list[str] = None

    def __post_init__(self) -> None:
        if self.reasons is None:
            self.reasons = []

    def to_dict(self) -> dict:
        return {"allowed": self.allowed, "reasons": self.reasons}
