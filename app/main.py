from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.config import get_settings
from app.pipeline import AgentPipeline

app = FastAPI(title="genai-agents", version="0.2.0")
settings = get_settings()


class AgentRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    use_rag: bool = True
    session_id: str = "default"


class AgentResponse(BaseModel):
    query: str
    answer: str
    provider: str
    model: str
    session_id: str = "default"
    context_sources: list[str] = []
    eval_scores: dict = {}
    usage: dict = {}
    cost_usd: float = 0.0
    guardrail_blocked: bool = False
    latency_ms: int = 0
    cache_hit: bool = False
    tier: str = ""


pipeline = AgentPipeline()


class Document(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)
    metadata: dict = {}


class IngestRequest(BaseModel):
    documents: list[Document] = Field(..., min_length=1, max_length=500)


class IngestResponse(BaseModel):
    ingested: int
    total: int


@app.post("/v1/agents/chat", response_model=AgentResponse)
async def agent_chat(req: AgentRequest) -> AgentResponse:
    result = await pipeline.run(req.query, use_rag=req.use_rag, session_id=req.session_id)
    return AgentResponse(**result.to_dict())


@app.post("/v1/documents", response_model=IngestResponse, status_code=201)
async def ingest_documents(req: IngestRequest) -> IngestResponse:
    result = await pipeline.ingest(
        [d.text for d in req.documents],
        metadata=[d.metadata for d in req.documents],
    )
    return IngestResponse(**result)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "provider": settings.llm_provider,
        "guardrails": settings.enable_guardrails,
        "memory_backend": settings.memory_backend,
    }


@app.get("/v1/cache/stats")
async def cache_stats() -> dict:
    return pipeline.cache.stats()
