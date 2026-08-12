import asyncio
from typing import List

import pytest

from app.providers.base import LLMProvider, LLMResponse, LLMUsage
from app.rag.embeddings import cosine_similarity
from app.rag.retriever import VectorStore


class FakeProvider(LLMProvider):
    name = "fake"

    async def generate(self, system: str, user: str, **kwargs) -> LLMResponse:
        return LLMResponse(text="fake answer", usage=LLMUsage(10, 20), model="fake")

    async def embed(self, texts: List[str]) -> List[List[float]]:
        return [[1.0 if "aws" in t.lower() else 0.0, 1.0 if "k8s" in t.lower() else 0.0] for t in texts]


@pytest.mark.asyncio
class TestVectorStore:
    async def test_add_and_search_returns_ranked(self):
        store = VectorStore(FakeProvider(), top_k=2)
        await store.add_documents(
            ["AWS is a cloud platform", "Kubernetes orchestrates containers", "The weather today is sunny"],
        )
        results = await store.search("What is AWS?")
        assert len(results) == 2
        assert "AWS" in results[0].text
        assert results[0].score >= results[1].score

    async def test_empty_store_returns_empty(self):
        store = VectorStore(FakeProvider())
        assert await store.search("anything") == []


class TestCosineSimilarity:
    def test_identical_vectors(self):
        assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_dimension_mismatch_raises(self):
        with pytest.raises(ValueError):
            cosine_similarity([1.0], [1.0, 2.0])
