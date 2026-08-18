from dataclasses import dataclass
from typing import Literal

from app.config import get_settings

Tier = Literal["cheap", "strong"]


@dataclass
class TierDecision:
    tier: Tier
    reason: str
    model: str


class ComplexityRouter:
    """Route a query to a cheaper or stronger model based on heuristics.

    Cost discipline: most queries are simple — don't pay for the strong model
    when the cheap one is enough. This is the "model tiering" Provectus asks about.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.cheap_model = settings.bedrock_cheap_model
        self.strong_model = settings.bedrock_model_id
        self.cheap_max_words = 8
        self.cheap_max_tokens = 256

    def decide(self, query: str) -> TierDecision:
        words = len(query.split())

        # Short, factual questions → cheap model
        if words <= self.cheap_max_words and self._is_factual(query):
            return TierDecision(
                tier="cheap",
                reason=f"short factual ({words} words)",
                model=self.cheap_model,
            )

        # Multi-step / reasoning → strong model
        if self._needs_reasoning(query):
            return TierDecision(
                tier="strong",
                reason="reasoning or multi-step",
                model=self.strong_model,
            )

        return TierDecision(tier="cheap", reason=f"default ({words} words)", model=self.cheap_model)

    def _is_factual(self, query: str) -> bool:
        q = query.lower()
        return any(
            k in q
            for k in (
                "what is",
                "who is",
                "when",
                "where",
                "capital of",
                "how many",
                "list",
            )
        )

    def _needs_reasoning(self, query: str) -> bool:
        q = query.lower()
        return any(
            k in q
            for k in (
                "compare",
                "explain why",
                "analyze",
                "evaluate",
                "pros and cons",
                "design",
                "architecture",
                "plan",
                "step by step",
            )
        )
