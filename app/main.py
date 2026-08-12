import time
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.agents.graph import build_graph
from app.agents.nodes import AnswerNode, RetrieverNode, Router
from app.config import get_settings
from app.costs.cache import ResponseCache
from app.costs.tiering import ComplexityRouter
from app.eval.cost import CostTracker
from app.eval.metrics import evaluate_answer
from app.guards import inspect_input, inspect_output
from app.logging_config import structured_log
from app.providers.factory import get_provider
from app.rag.retriever import VectorStore

app = FastAPI(title="genai-agents", version="0.1.0")
settings = get_settings()


class AgentRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    use_rag: bool = True


class AgentResponse(BaseModel):
    query: str
    answer: str
    provider: str
    model: str
    context_sources: List[str] = []
    eval_scores: dict = {}
    usage: dict = {}
    cost_usd: float = 0.0
    guardrail_blocked: bool = False
    latency_ms: int = 0
    cache_hit: bool = False
    tier: str = ""


def _init_services():
    provider = get_provider()
    store = VectorStore(provider)
    retriever = RetrieverNode(provider, store)
    answerer = AnswerNode(provider)
    graph = build_graph(retriever, answerer, Router())
    return provider, store, graph


provider, store, graph = _init_services()
tier_router = ComplexityRouter()
response_cache = ResponseCache(ttl_seconds=3600)


@app.post("/v1/agents/chat", response_model=AgentResponse)
async def agent_chat(req: AgentRequest) -> AgentResponse:
    started = time.monotonic()
    tracker = CostTracker()

    guard = inspect_input(req.query)
    if not guard.allowed:
        structured_log("WARN", "guardrail.blocked", reasons=guard.reasons)
        return AgentResponse(
            query=req.query,
            answer="Request blocked by input guardrails.",
            provider=settings.llm_provider,
            model=settings.llm_model,
            guardrail_blocked=True,
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    tier = tier_router.decide(req.query)
    model = tier.model

    # Cost discipline: return cached response when the same query+model repeats.
    cached = response_cache.get(req.query, model)
    if cached is not None:
        latency_ms = int((time.monotonic() - started) * 1000)
        structured_log(
            "INFO", "agent.chat", query_len=len(req.query), latency_ms=latency_ms,
            cost_usd=0.0, cache_hit=True, tier=tier.tier,
        )
        return AgentResponse(
            query=req.query,
            answer=cached["answer"],
            provider=cached["provider"],
            model=cached["model"],
            context_sources=cached.get("context_sources", []),
            eval_scores=cached.get("eval_scores", {}),
            usage=cached.get("usage", {}),
            cost_usd=0.0,
            latency_ms=latency_ms,
            cache_hit=True,
            tier=tier.tier,
        )

    state = {
        "query": req.query,
        "use_rag": req.use_rag,
    }

    result = await graph.ainvoke(state)

    answer = result.get("answer", "")
    output_guard, sanitized = inspect_output(answer)
    if output_guard.reasons:
        answer = sanitized

    context = result.get("context", "")
    sources = [line.split("]", 1)[0].strip("[]") for line in context.splitlines() if line.strip()]

    claims = answer.split(". ")
    eval_results = evaluate_answer(
        answer=answer,
        query=req.query,
        context=context,
        claims=claims,
        threshold=0.5,
    )
    eval_scores = {r.metric: r.score for r in eval_results}

    usage = {
        "input_tokens": result.get("input_tokens", 0),
        "output_tokens": result.get("output_tokens", 0),
    }

    from app.providers.base import LLMUsage

    tracker.add(
        LLMUsage(
            input_tokens=result.get("input_tokens", 0),
            output_tokens=result.get("output_tokens", 0),
        )
    )
    cost = tracker.estimate()

    latency_ms = int((time.monotonic() - started) * 1000)
    structured_log(
        "INFO",
        "agent.chat",
        query_len=len(req.query),
        latency_ms=latency_ms,
        cost_usd=cost.total,
        cache_hit=False,
        tier=tier.tier,
    )

    response = AgentResponse(
        query=req.query,
        answer=answer,
        provider=result.get("provider", settings.llm_provider),
        model=result.get("model", settings.llm_model),
        context_sources=sources,
        eval_scores=eval_scores,
        usage=usage,
        cost_usd=round(cost.total, 6),
        latency_ms=latency_ms,
        cache_hit=False,
        tier=tier.tier,
    )

    # Store response keyed by the tier-resolved model for future hits.
    response_cache.set(req.query, model, {
        "answer": answer,
        "provider": result.get("provider", settings.llm_provider),
        "model": result.get("model", settings.llm_model),
        "context_sources": sources,
        "eval_scores": eval_scores,
        "usage": usage,
    })

    return response


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "provider": settings.llm_provider,
        "guardrails": settings.enable_guardrails,
    }


@app.get("/v1/cache/stats")
async def cache_stats() -> dict:
    return response_cache.stats()
