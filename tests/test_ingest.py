"""Tests for the document ingestion path (AgentPipeline.ingest).

Uses injected provider + store so no API key, network or SDK is needed.
"""

import pytest

from app.agents.memory import InMemoryConversationMemory
from app.pipeline import AgentPipeline
from app.providers.base import LLMProvider, LLMResponse, LLMUsage
from app.rag.retriever import VectorStore


class FakeProvider(LLMProvider):
    name = "fake"

    async def generate(self, system: str, user: str, **kwargs) -> LLMResponse:
        return LLMResponse(text="answer", usage=LLMUsage(1, 1), model="fake")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t)), 0.0] for t in texts]


class EnsureTrackingStore(VectorStore):
    """In-memory store that also records ensure_index() calls (like S3VectorStore)."""

    def __init__(self, provider):
        super().__init__(provider)
        self.ensure_calls = 0

    def ensure_index(self) -> None:
        self.ensure_calls += 1


def _pipeline(store):
    provider = FakeProvider()
    return AgentPipeline(
        provider=provider,
        store=store,
        memory=InMemoryConversationMemory(),
    )


@pytest.mark.asyncio
async def test_ingest_adds_documents_and_reports_counts():
    store = VectorStore(FakeProvider())
    pipe = _pipeline(store)

    result = await pipe.ingest(["doc one", "doc two"])

    assert result == {"ingested": 2, "total": 2}
    assert store.size == 2


@pytest.mark.asyncio
async def test_ingest_empty_is_noop():
    store = VectorStore(FakeProvider())
    pipe = _pipeline(store)
    result = await pipe.ingest([])
    assert result == {"ingested": 0, "total": 0}


@pytest.mark.asyncio
async def test_ingest_calls_ensure_index_once():
    store = EnsureTrackingStore(FakeProvider())
    pipe = _pipeline(store)

    await pipe.ingest(["a"])
    await pipe.ingest(["b"])

    # ensure_index runs only on the first ingest (index bootstrap), not every call.
    assert store.ensure_calls == 1
    assert store.size == 2


@pytest.mark.asyncio
async def test_ingest_invalidates_response_cache():
    store = VectorStore(FakeProvider())
    pipe = _pipeline(store)
    # Seed a stale cached answer, then ingest new docs.
    pipe.cache.set("old query", "m", {"answer": "stale"})
    assert pipe.cache.stats()["size"] == 1

    await pipe.ingest(["new doc"])

    assert pipe.cache.stats()["size"] == 0
    assert pipe.cache.get("old query", "m") is None


@pytest.mark.asyncio
async def test_ingest_passes_metadata_through():
    store = VectorStore(FakeProvider())
    pipe = _pipeline(store)

    await pipe.ingest(["hello"], metadata=[{"src": "wiki"}])

    docs = await store.search("hello")
    assert docs[0].metadata == {"src": "wiki"}
