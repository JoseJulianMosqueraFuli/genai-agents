import asyncio
from dataclasses import dataclass, field
from typing import List

from app.logging_config import structured_log
from app.providers.base import LLMProvider
from app.rag.embeddings import cosine_similarity


@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)
    vector: List[float] = field(default_factory=list)


@dataclass
class RetrievedDoc:
    chunk_id: str
    text: str
    score: float
    metadata: dict = field(default_factory=dict)


class VectorStore:
    """In-memory vector store backed by a provider's embedding model."""

    def __init__(self, provider: LLMProvider, top_k: int = 4) -> None:
        self.provider = provider
        self.top_k = top_k
        self.chunks: List[Chunk] = []

    async def add_documents(self, texts: List[str], metadata: List[dict] | None = None) -> None:
        vectors = await self.provider.embed(texts)
        for i, (text, vector) in enumerate(zip(texts, vectors)):
            meta = (metadata or [{}] * len(texts))[i] if metadata else {}
            self.chunks.append(Chunk(id=f"c{len(self.chunks)}", text=text, metadata=meta, vector=vector))
        structured_log("INFO", "rag.add_documents", count=len(texts), total=len(self.chunks))

    async def search(self, query: str) -> List[RetrievedDoc]:
        if not self.chunks:
            return []
        query_vector = (await self.provider.embed([query]))[0]
        scored = [
            (cosine_similarity(query_vector, chunk.vector), chunk)
            for chunk in self.chunks
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [
            RetrievedDoc(
                chunk_id=chunk.id,
                text=chunk.text,
                score=score,
                metadata=chunk.metadata,
            )
            for score, chunk in scored[: self.top_k]
        ]
        structured_log("INFO", "rag.search", query_len=len(query), hits=len(results))
        return results

    @property
    def size(self) -> int:
        return len(self.chunks)


async def build_context(store: VectorStore, query: str) -> tuple[str, List[RetrievedDoc]]:
    docs = await store.search(query)
    context = "\n\n".join(f"[{d.chunk_id}] {d.text}" for d in docs)
    return context, docs
