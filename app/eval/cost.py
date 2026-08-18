"""Per-request token accounting and cost estimation for observability.

Cost is estimated per model, not with a single flat rate: a query routed to the
cheap tier (e.g. Amazon Nova Micro) should not be billed like the strong tier
(Nova Pro). ``CostTracker`` looks up a per-model price and only falls back to the
flat default when a model is unknown or unset — so the tiering router's cost
discipline is reflected in the reported spend, not just in which model runs.
"""

from dataclasses import dataclass

from app.providers.base import LLMUsage


@dataclass(frozen=True)
class ModelPricing:
    """USD price per 1K tokens for a single model."""

    input_per_1k: float
    output_per_1k: float


# Approximate public list prices (USD per 1K tokens). These are intentionally a
# static table: cost reporting is an observability signal, not billing. Keys are
# matched exactly first, then as a substring so region-prefixed Bedrock inference
# profile ids (e.g. "us.amazon.nova-pro-v1:0") resolve to the base model price.
MODEL_PRICING: dict[str, ModelPricing] = {
    # Amazon Nova (generation)
    "amazon.nova-micro-v1:0": ModelPricing(0.000035, 0.00014),
    "amazon.nova-lite-v1:0": ModelPricing(0.00006, 0.00024),
    "amazon.nova-pro-v1:0": ModelPricing(0.0008, 0.0032),
    # Amazon Titan (embeddings) — output priced at 0 (embeddings return no tokens).
    "amazon.titan-embed-text-v2:0": ModelPricing(0.00002, 0.0),
}


def pricing_for(model: str, default: ModelPricing) -> ModelPricing:
    """Resolve the price for ``model``, falling back to ``default`` if unknown.

    Tries an exact match, then a substring match so inference-profile ids that
    prefix the base model name (``us.amazon.nova-pro-v1:0``) still resolve.
    """
    if model:
        exact = MODEL_PRICING.get(model)
        if exact is not None:
            return exact
        for key, price in MODEL_PRICING.items():
            if key in model:
                return price
    return default


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
    """Track per-request token usage and estimate cost for observability.

    ``input_price_per_1k`` / ``output_price_per_1k`` are the fallback rate used
    for usage recorded without a model (or for models absent from
    ``MODEL_PRICING``). When ``add`` is given a ``model``, its per-model price
    from the table is used instead.
    """

    def __init__(
        self, input_price_per_1k: float = 0.00015, output_price_per_1k: float = 0.0006
    ) -> None:
        self.default_pricing = ModelPricing(input_price_per_1k, output_price_per_1k)
        self._history: list[tuple[LLMUsage, str]] = []

    def add(self, usage: LLMUsage, model: str = "") -> None:
        self._history.append((usage, model))

    def estimate(self) -> CostEstimate:
        total_in = 0
        total_out = 0
        input_cost = 0.0
        output_cost = 0.0
        for usage, model in self._history:
            pricing = pricing_for(model, self.default_pricing)
            total_in += usage.input_tokens
            total_out += usage.output_tokens
            input_cost += usage.input_tokens / 1000 * pricing.input_per_1k
            output_cost += usage.output_tokens / 1000 * pricing.output_per_1k
        return CostEstimate(
            input_tokens=total_in,
            output_tokens=total_out,
            input_cost=round(input_cost, 6),
            output_cost=round(output_cost, 6),
        )

    def reset(self) -> None:
        self._history.clear()

    @property
    def request_count(self) -> int:
        return len(self._history)
