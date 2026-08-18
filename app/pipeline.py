"""Shared agent pipeline: guardrails -> tiering -> cache -> graph -> eval -> cost.

Both entrypoints reuse this so behaviour stays identical regardless of how the
agent is served:

- `app/main.py` — FastAPI service (ECS Fargate deployment).
- `app/runtime/agentcore_app.py` — Amazon Bedrock AgentCore Runtime entrypoint.

Keeping the orchestration in one place is the "organize" fix: there is a single
source of truth for the request lifecycle instead of duplicated logic per runtime.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

from app.agents.graph import build_graph
from app.agents.memory import ConversationMemory, Turn, get_memory
from app.agents.nodes import AnswerNode, RetrieverNode
from app.config import Settings, get_settings
from app.costs.cache import ResponseCache
from app.costs.tiering import ComplexityRouter
from app.eval.cost import CostTracker
from app.eval.metrics import evaluate_answer
from app.guards import inspect_input, inspect_output
from app.logging_config import structured_log
from app.providers.base import LLMProvider, LLMUsage
from app.providers.factory import get_provider
from app.rag.factory import get_vector_store
from app.rag.retriever import VectorStore


@dataclass
class AgentResult:
    query: str
    answer: str
    provider: str
    model: str
    session_id: str = "default"
    context_sources: list[str] = field(default_factory=list)
    eval_scores: dict = field(default_factory=dict)
    usage: dict = field(default_factory=dict)
    cost_usd: float = 0.0
    guardrail_blocked: bool = False
    latency_ms: int = 0
    cache_hit: bool = False
    tier: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class AgentPipeline:
    """Runtime-agnostic orchestration of a single agent turn."""

    def __init__(
        self,
        *,
        provider: LLMProvider | None = None,
        store: VectorStore | None = None,
        graph=None,
        tier_router: ComplexityRouter | None = None,
        cache: ResponseCache | None = None,
        memory: ConversationMemory | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.provider = provider or get_provider()
        self.store = store or get_vector_store(self.provider, self.settings)
        self.graph = graph or build_graph(
            RetrieverNode(self.provider, self.store), AnswerNode(self.provider)
        )
        self.tier_router = tier_router or ComplexityRouter()
        self.cache = cache or ResponseCache(ttl_seconds=3600)
        self.memory = memory if memory is not None else get_memory()
        self._index_ready = False

    async def run(
        self, query: str, use_rag: bool = True, session_id: str = "default"
    ) -> AgentResult:
        started = time.monotonic()

        guard = inspect_input(query)
        if not guard.allowed:
            structured_log("WARN", "guardrail.blocked", reasons=guard.reasons)
            return AgentResult(
                query=query,
                answer="Request blocked by input guardrails.",
                provider=self.settings.llm_provider,
                model=self.settings.llm_model,
                session_id=session_id,
                guardrail_blocked=True,
                latency_ms=self._elapsed_ms(started),
            )

        tier = self.tier_router.decide(query)
        model = tier.model

        cached = self.cache.get(query, model)
        if cached is not None:
            latency_ms = self._elapsed_ms(started)
            structured_log(
                "INFO",
                "agent.chat",
                query_len=len(query),
                latency_ms=latency_ms,
                cost_usd=0.0,
                cache_hit=True,
                tier=tier.tier,
                session_id=session_id,
            )
            return AgentResult(
                query=query,
                answer=cached["answer"],
                provider=cached["provider"],
                model=cached["model"],
                session_id=session_id,
                context_sources=cached.get("context_sources", []),
                eval_scores=cached.get("eval_scores", {}),
                usage=cached.get("usage", {}),
                cost_usd=0.0,
                latency_ms=latency_ms,
                cache_hit=True,
                tier=tier.tier,
            )

        history = self._render_history(session_id)
        state = {
            "query": query,
            "use_rag": use_rag,
            "session_id": session_id,
            "history": history,
            # Route the tier-selected model to the LLM (cost discipline, for real).
            "model": model,
        }
        result = await self.graph.ainvoke(state)

        answer = result.get("answer", "")
        output_guard, sanitized = inspect_output(answer)
        if output_guard.reasons:
            answer = sanitized

        context = result.get("context", "")
        sources = [
            line.split("]", 1)[0].strip("[]") for line in context.splitlines() if line.strip()
        ]

        claims = answer.split(". ")
        eval_results = evaluate_answer(
            answer=answer, query=query, context=context, claims=claims, threshold=0.5
        )
        eval_scores = {r.metric: r.score for r in eval_results}

        usage = {
            "input_tokens": result.get("input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0),
        }

        tracker = CostTracker(
            input_price_per_1k=self.settings.cost_per_1k_input_tokens,
            output_price_per_1k=self.settings.cost_per_1k_output_tokens,
        )
        # Bill against the model that actually ran (tier-selected), so cheap/strong
        # routing shows up in reported cost, not just in the cache key.
        tracker.add(
            LLMUsage(input_tokens=usage["input_tokens"], output_tokens=usage["output_tokens"]),
            model=model,
        )
        cost = tracker.estimate()

        # Persist the turn so follow-up questions in the same session stay coherent.
        self.memory.append(session_id, "user", query)
        self.memory.append(session_id, "assistant", answer)

        latency_ms = self._elapsed_ms(started)
        structured_log(
            "INFO",
            "agent.chat",
            query_len=len(query),
            latency_ms=latency_ms,
            cost_usd=cost.total,
            cache_hit=False,
            tier=tier.tier,
            session_id=session_id,
        )

        provider_name = result.get("provider", self.settings.llm_provider)
        model_name = result.get("model", self.settings.llm_model)

        self.cache.set(
            query,
            model,
            {
                "answer": answer,
                "provider": provider_name,
                "model": model_name,
                "context_sources": sources,
                "eval_scores": eval_scores,
                "usage": usage,
            },
        )

        return AgentResult(
            query=query,
            answer=answer,
            provider=provider_name,
            model=model_name,
            session_id=session_id,
            context_sources=sources,
            eval_scores=eval_scores,
            usage=usage,
            cost_usd=round(cost.total, 6),
            latency_ms=latency_ms,
            cache_hit=False,
            tier=tier.tier,
        )

    def _ensure_store_ready(self) -> None:
        """Create the vector index if the backend needs it (S3 Vectors). Once per process."""
        if self._index_ready:
            return
        ensure = getattr(self.store, "ensure_index", None)
        if callable(ensure):
            ensure()
        self._index_ready = True

    async def ingest(self, documents: list[str], metadata: list[dict] | None = None) -> dict:
        """Embed and store documents into the vector backend.

        This is the "how data gets into RAG" path: for S3 Vectors it also creates the
        bucket/index on first call. Returns counts for the caller.
        """
        if not documents:
            return {"ingested": 0, "total": self.store.size}
        self._ensure_store_ready()
        await self.store.add_documents(documents, metadata=metadata)
        # New documents change what retrieval returns, so cached answers are now
        # stale — drop the response cache to avoid serving pre-ingest answers.
        self.cache.clear()
        structured_log("INFO", "rag.ingest", count=len(documents), total=self.store.size)
        return {"ingested": len(documents), "total": self.store.size}

    def _render_history(self, session_id: str) -> str:
        turns: list[Turn] = self.memory.history(session_id)
        if not turns:
            return ""
        window = turns[-self.settings.memory_window :]
        return "\n".join(f"{t.role.capitalize()}: {t.content}" for t in window)

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return int((time.monotonic() - started) * 1000)
