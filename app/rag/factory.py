"""Vector store selection by config, mirroring the LLM/memory strategy.

``VECTOR_BACKEND=in_memory`` (default) keeps the zero-dependency store used in dev
and tests. ``VECTOR_BACKEND=s3_vectors`` swaps in Amazon S3 Vectors with no change to
the agent code — the pipeline only talks to the `VectorStore` contract.
"""

from __future__ import annotations

from app.config import Settings, get_settings
from app.logging_config import structured_log
from app.providers.base import LLMProvider
from app.rag.retriever import VectorStore


def get_vector_store(provider: LLMProvider, settings: Settings | None = None):
    """Return the configured vector store backend."""
    settings = settings or get_settings()

    if settings.vector_backend == "s3_vectors":
        from app.rag.s3_vectors import S3VectorStore

        structured_log(
            "INFO",
            "rag.backend",
            backend="s3_vectors",
            bucket=settings.s3_vectors_bucket,
            index=settings.s3_vectors_index,
        )
        return S3VectorStore(
            provider,
            bucket=settings.s3_vectors_bucket,
            index=settings.s3_vectors_index,
            top_k=settings.retrieval_top_k,
            region=settings.bedrock_region,
            dimension=settings.embedding_dimension,
        )

    structured_log("INFO", "rag.backend", backend="in_memory")
    return VectorStore(provider, top_k=settings.retrieval_top_k)
