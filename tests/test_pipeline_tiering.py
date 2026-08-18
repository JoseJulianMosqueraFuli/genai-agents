"""Full-pipeline test: the tiering router's model choice must reach the LLM.

Guards against regressing the "cost discipline" fix — previously `tier.model` was
only used as a cache key and never routed to `provider.generate`.
"""

import pytest

from app.agents.memory import InMemoryConversationMemory
from app.costs.tiering import TierDecision
from app.pipeline import AgentPipeline
from app.providers.base import LLMProvider, LLMResponse, LLMUsage
from app.rag.retriever import VectorStore


class RecordingProvider(LLMProvider):
    """Records the model passed to generate and echoes it back on the response."""

    name = "rec"

    def __init__(self):
        self.last_model = None

    async def generate(self, system: str, user: str, **kwargs) -> LLMResponse:
        self.last_model = kwargs.get("model")
        return LLMResponse(
            text="grounded answer",
            usage=LLMUsage(5, 7),
            model=kwargs.get("model") or "default",
        )

    async def embed(self, texts):
        return [[0.0, 0.0] for _ in texts]


class StubRouter:
    def __init__(self, tier: str, model: str):
        self._decision = TierDecision(tier=tier, reason="test", model=model)

    def decide(self, query: str) -> TierDecision:
        return self._decision


def _pipeline(provider, router):
    return AgentPipeline(
        provider=provider,
        store=VectorStore(provider),
        tier_router=router,
        memory=InMemoryConversationMemory(),
    )


@pytest.mark.asyncio
async def test_cheap_tier_model_reaches_generation():
    provider = RecordingProvider()
    pipe = _pipeline(provider, StubRouter("cheap", "cheap-model"))

    result = await pipe.run("what is aws?")

    assert provider.last_model == "cheap-model"
    assert result.model == "cheap-model"
    assert result.tier == "cheap"


@pytest.mark.asyncio
async def test_strong_tier_model_reaches_generation():
    provider = RecordingProvider()
    pipe = _pipeline(provider, StubRouter("strong", "strong-model"))

    result = await pipe.run("compare and analyze the tradeoffs of x versus y in depth")

    assert provider.last_model == "strong-model"
    assert result.model == "strong-model"
    assert result.tier == "strong"


@pytest.mark.asyncio
async def test_cache_key_is_per_model_tier():
    provider = RecordingProvider()
    pipe = _pipeline(provider, StubRouter("cheap", "cheap-model"))

    await pipe.run("same question")
    result2 = await pipe.run("same question")

    # Second identical (query, model) hits the cache — no second LLM call, $0 cost.
    assert result2.cache_hit is True
    assert result2.cost_usd == 0.0
