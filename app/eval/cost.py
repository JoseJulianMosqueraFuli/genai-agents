from dataclasses import dataclass

from app.providers.base import LLMUsage


@dataclass
class CostEstimate:
    input_tokens: int = 0
    output_tokens: int = 0
    input_cost: float = 0.0
    output_cost: float = 0.0

    @property
    def total(self) -> float:
        return self.input_cost + self.output_cost


class CostTracker:
    """Track per-request token usage and estimate cost for observability."""

    def __init__(
        self, input_price_per_1k: float = 0.00015, output_price_per_1k: float = 0.0006
    ) -> None:
        self.input_price_per_1k = input_price_per_1k
        self.output_price_per_1k = output_price_per_1k
        self._history: list[LLMUsage] = []

    def add(self, usage: LLMUsage) -> None:
        self._history.append(usage)

    def estimate(self) -> CostEstimate:
        total_in = sum(u.input_tokens for u in self._history)
        total_out = sum(u.output_tokens for u in self._history)
        return CostEstimate(
            input_tokens=total_in,
            output_tokens=total_out,
            input_cost=round(total_in / 1000 * self.input_price_per_1k, 6),
            output_cost=round(total_out / 1000 * self.output_price_per_1k, 6),
        )

    def reset(self) -> None:
        self._history.clear()

    @property
    def request_count(self) -> int:
        return len(self._history)
