import pytest

from app.agents.graph import build_graph
from app.agents.nodes import AnswerNode, RetrieverNode, Router
from app.providers.base import LLMProvider, LLMResponse, LLMUsage
from app.rag.retriever import VectorStore


class FakeProvider(LLMProvider):
    name = "fake"
    _embeds = {
        "aws cloud": [1.0, 0.0],
        "kubernetes": [0.0, 1.0],
    }

    async def generate(self, system: str, user: str, **kwargs) -> LLMResponse:
        return LLMResponse(
            text="A grounded answer about the context", usage=LLMUsage(20, 30), model="fake"
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embeds.get(t.lower(), [0.0, 0.0]) for t in texts]


@pytest.mark.asyncio
async def test_full_graph_invocation():
    provider = FakeProvider()
    store = VectorStore(provider, top_k=2)
    await store.add_documents(["AWS is a cloud platform", "Kubernetes orchestrates containers"])

    retriever = RetrieverNode(provider, store)
    answerer = AnswerNode(provider)
    graph = build_graph(retriever, answerer, Router())

    state = {"query": "aws cloud", "use_rag": True}
    result = await graph.ainvoke(state)

    assert result["answer"] == "A grounded answer about the context"
    assert result["provider"] == "fake"
    assert result["input_tokens"] == 20
    assert result["output_tokens"] == 30
    assert "AWS" in result["context"]


@pytest.mark.asyncio
async def test_empty_store_still_answers():
    provider = FakeProvider()
    store = VectorStore(provider, top_k=2)
    retriever = RetrieverNode(provider, store)
    answerer = AnswerNode(provider)
    graph = build_graph(retriever, answerer, Router())

    result = await graph.ainvoke({"query": "hello", "use_rag": True})
    assert result["answer"]
    assert result["context"] == ""
