from dataclasses import dataclass
from typing import Dict, List


@dataclass
class GuardrailResult:
    allowed: bool
    reasons: List[str] = None

    def __post_init__(self) -> None:
        if self.reasons is None:
            self.reasons = []

    def to_dict(self) -> dict:
        return {"allowed": self.allowed, "reasons": self.reasons}
