"""Tests for the Amazon S3 Vectors RAG backend.

No network, no AWS: a fake ``s3vectors`` client records writes and returns canned
query hits, so we exercise the full add/search mapping without boto3 or credentials.
"""

import pytest

from app.providers.base import LLMProvider, LLMResponse, LLMUsage
from app.rag.s3_vectors import S3VectorStore


class FakeProvider(LLMProvider):
    name = "fake"

    async def generate(self, system: str, user: str, **kwargs) -> LLMResponse:
        return LLMResponse(text="x", usage=LLMUsage(1, 1), model="fake")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # deterministic 2-dim embeddings
        return [
            [1.0 if "aws" in t.lower() else 0.0, 1.0 if "k8s" in t.lower() else 0.0] for t in texts
        ]


class FakeS3VectorsClient:
    def __init__(self, query_hits=None):
        self.put_calls = []
        self.created_indexes = []
        self.created_buckets = []
        self._query_hits = query_hits or []

    def create_vector_bucket(self, **kwargs):
        self.created_buckets.append(kwargs)

    def create_index(self, **kwargs):
        self.created_indexes.append(kwargs)

    def put_vectors(self, **kwargs):
        self.put_calls.append(kwargs)

    def query_vectors(self, **kwargs):
        self.last_query = kwargs
        return {"vectors": self._query_hits}


def _store(client, **kw):
    return S3VectorStore(FakeProvider(), bucket="b", index="i", client=client, **kw)


def test_requires_bucket_and_index():
    with pytest.raises(ValueError):
        S3VectorStore(FakeProvider(), bucket="", index="i", client=FakeS3VectorsClient())


@pytest.mark.asyncio
async def test_add_documents_puts_vectors_with_text_metadata():
    client = FakeS3VectorsClient()
    store = _store(client)
    await store.add_documents(["AWS is a cloud platform", "K8s orchestrates containers"])

    assert len(client.put_calls) == 1
    vectors = client.put_calls[0]["vectors"]
    assert len(vectors) == 2
    assert vectors[0]["data"]["float32"] == [1.0, 0.0]
    assert vectors[0]["metadata"]["text"] == "AWS is a cloud platform"
    assert store.size == 2


@pytest.mark.asyncio
async def test_add_documents_batches_over_500():
    client = FakeS3VectorsClient()
    store = _store(client)
    await store.add_documents([f"doc {i}" for i in range(501)])
    assert len(client.put_calls) == 2
    assert len(client.put_calls[0]["vectors"]) == 500
    assert len(client.put_calls[1]["vectors"]) == 1


@pytest.mark.asyncio
async def test_search_maps_hits_to_retrieved_docs():
    hits = [
        {
            "key": "k1",
            "distance": 0.1,
            "metadata": {"text": "AWS is a cloud platform", "src": "doc1"},
        },
        {"key": "k2", "distance": 0.4, "metadata": {"text": "K8s orchestrates containers"}},
    ]
    client = FakeS3VectorsClient(query_hits=hits)
    store = _store(client, top_k=2)

    results = await store.search("what is aws?")

    assert client.last_query["topK"] == 2
    assert client.last_query["returnMetadata"] is True
    assert [r.chunk_id for r in results] == ["k1", "k2"]
    assert results[0].text == "AWS is a cloud platform"
    # cosine distance 0.1 -> similarity 0.9; text stripped from surfaced metadata
    assert results[0].score == pytest.approx(0.9)
    assert "text" not in results[0].metadata
    assert results[0].metadata["src"] == "doc1"


@pytest.mark.asyncio
async def test_search_empty_index_returns_empty():
    store = _store(FakeS3VectorsClient(query_hits=[]))
    assert await store.search("anything") == []


def test_ensure_index_is_idempotent_and_declares_text_nonfilterable():
    client = FakeS3VectorsClient()
    store = _store(client, dimension=1024)
    store.ensure_index()
    assert client.created_buckets[0]["vectorBucketName"] == "b"
    idx = client.created_indexes[0]
    assert idx["dimension"] == 1024
    assert idx["distanceMetric"] == "cosine"
    assert idx["metadataConfiguration"]["nonFilterableMetadataKeys"] == ["text"]
