# GenAI Agents

[![CI](https://github.com/JoseJulianMosqueraFuli/genai-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/JoseJulianMosqueraFuli/genai-agents/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C.svg)](https://langchain-ai.github.io/langgraph/)

English | [Español](README.es.md)

Production-grade GenAI agent platform: **RAG** (retrieval-augmented generation) + **multi-provider LLMs** (OpenAI / AWS Bedrock) + **LangGraph** orchestration + **guardrails** (PII redaction, prompt-injection defense) + **evaluation** (faithfulness, answer relevance) + **cost tracking** — all behind a FastAPI service, containerized and CI-tested.

## Why this project?

Most GenAI demos stop at "call an LLM". This one is built like a production service:

- **Multi-LLM strategy** via a provider interface — swap OpenAI for Bedrock (Claude) with one env var.
- **RAG pipeline** with vector search over your documents (embeddings + cosine similarity).
- **LangGraph agent** wiring retrieval → grounding → answer, so every response is traceable.
- **Guardrails** on input (prompt injection) and output (PII redaction) — required for real clients.
- **Eval + observability**: faithfulness / answer-relevance scores and per-request cost in USD.
- **TDD**: 25 tests, all external providers mocked — CI runs them on every push.

## Architecture

```
 User query
     │
     ▼
[Guardrails: input] ──blocked?──► 403 semantics
     │ allowed
     ▼
[LangGraph Agent]
   retrieve ──► embed query ──► vector search ──► top-k chunks
     │
     ▼
   answer ──► LLM (OpenAI | Bedrock) grounded on context
     │
     ▼
[Guardrails: output] ── PII redaction
     │
     ▼
[Eval: faithfulness + relevance] ──► [Cost tracking (USD)]
     │
     ▼
  JSON response
```

## Quick Start

```bash
cp .env.example .env   # fill OPENAI_API_KEY (or switch to BEDROCK)
uv sync                # creates .venv from pyproject.toml + uv.lock
uv run uvicorn app.main:app --reload
```

> Uses [uv](https://docs.astral.sh/uv/) for dependency management. Install it with
> `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `pipx install uv`).

```bash
# 1. Ingest documents into the RAG store
curl -s -X POST http://localhost:8000/v1/documents \
  -H 'Content-Type: application/json' \
  -d '{"documents":[{"text":"Kubernetes is a container orchestration platform."}]}'

# 2. Ask a grounded question
curl -s http://localhost:8000/v1/agents/chat \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is Kubernetes?"}'
```

### Docker

```bash
docker compose up --build
# API → http://localhost:8000   health → /health
```

### Tests

```bash
docker compose run --rm test-api        # or:
uv run pytest tests/ -v
```

## Configuration (`.env`)

| Variable                    | Default                                   | Description                     |
| --------------------------- | ----------------------------------------- | ------------------------------- |
| `LLM_PROVIDER`              | `openai`                                  | `openai` or `bedrock`           |
| `LLM_MODEL`                 | `gpt-4o-mini`                             | Model for OpenAI                |
| `BEDROCK_MODEL_ID`          | `anthropic.claude-3-5-sonnet-20240620-v1` | Claude via Bedrock              |
| `EMBEDDING_MODEL`           | `text-embedding-3-small`                  | Embeddings model                |
| `ENABLE_GUARDRAILS`         | `true`                                    | Toggle input/output guards      |
| `COST_PER_1K_INPUT_TOKENS`  | `0.00015`                                 | $/1k input tokens (cost model)  |
| `COST_PER_1K_OUTPUT_TOKENS` | `0.0006`                                  | $/1k output tokens (cost model) |

## API

### `POST /v1/agents/chat`

```json
{
  "query": "What is Kubernetes?",
  "use_rag": true
}
```

```json
{
  "query": "What is Kubernetes?",
  "answer": "Kubernetes is a container orchestration platform...",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "context_sources": ["c1", "c2"],
  "eval_scores": { "faithfulness": 1.0, "answer_relevance": 0.5 },
  "usage": { "input_tokens": 120, "output_tokens": 80 },
  "cost_usd": 0.000066,
  "guardrail_blocked": false,
  "latency_ms": 340
}
```

### `POST /v1/documents`

Ingest documents into the RAG vector store — this is how data gets into retrieval.
Embeds each document with the configured provider and stores it; for the S3 Vectors
backend it also creates the bucket/index on first call.

```json
{
  "documents": [
    {
      "text": "Kubernetes orchestrates containers.",
      "metadata": { "src": "k8s-docs" }
    },
    { "text": "AWS Fargate runs containers without managing servers." }
  ]
}
```

```json
{ "ingested": 2, "total": 2 }
```

```bash
curl -s -X POST http://localhost:8000/v1/documents \
  -H 'Content-Type: application/json' \
  -d '{"documents":[{"text":"Kubernetes orchestrates containers."}]}'
```

### `GET /health`

```json
{
  "status": "ok",
  "app": "genai-agents",
  "provider": "openai",
  "guardrails": true
}
```

### `GET /v1/cache/stats`

Cache hit-rate for the response cache (cost discipline):

```json
{ "size": 12, "hits": 34, "misses": 12, "hit_rate": 0.739 }
```

## Cost discipline: tiering + caching

Two mechanisms Provectus-style cost discipline, both live in `app/costs/`:

- **Model tiering** (`costs/tiering.py`): a `ComplexityRouter` sends short/factual queries to the cheap model (`gpt-4o-mini`) and reasoning/multi-step ones to the strong model. Not every question deserves Sonnet.
- **Response caching** (`costs/cache.py`): identical (query, model) pairs return from an in-memory cache with TTL — a cache hit costs **$0.00** and ~0ms. See `GET /v1/cache/stats`.

## Measured release gates

The `eval/` harness is what gates a release — the _"what you measured, how you produced ground truth, what gated a release"_ question:

```
eval/
├── dataset/qa.json      # 5 questions + expected answers (ground truth)
├── harness.py           # EvalRunner (scores each answer) + ReleaseGate (thresholds)
└── test_eval_gates.py   # CI: runs the dataset through a mock answerer
```

A release is promoted only if the gate passes:

```json
{
  "avg_faithfulness": 0.87,
  "avg_relevance": 0.82,
  "thresholds": { "faithfulness": 0.6, "relevance": 0.5 },
  "passed": true,
  "num_questions": 5
}
```

Run it:

```bash
pytest eval/test_eval_gates.py -v
```

In production you wire the `EvalRunner` to the real agent and block the pipeline on `ReleaseGate.evaluate()`. The `releases/` folder holds the per-release report (what was measured, thresholds, outcome).

## Roadmap

- [x] Multi-turn conversation memory (in-memory + Amazon Bedrock AgentCore Memory)
- [x] Serve on Amazon Bedrock AgentCore Runtime (managed, session-isolated)
- [x] Managed vector store — Amazon S3 Vectors (via SDK) with Titan v2 embeddings
- [x] Full-AWS model stack — Amazon Nova (generation) + Titan Text Embeddings V2
- [ ] Document chunking + file upload for ingestion (`POST /v1/documents` currently takes pre-chunked text)
- [ ] Evaluation with RAGAS-style metrics and a regression dataset
- [ ] Model A/B routing and canary deployments
- [ ] Guardrail-as-code policies (budget caps, topic allowlists)
- [ ] AgentCore Gateway (expose tools as MCP) + AgentCore Identity
- [x] Lint/format with `ruff` (config in `pyproject.toml`) wired into CI
- [ ] Prometheus metrics for latency, cost and eval drift

## Deploy on AWS (ECS Fargate Spot)

The project ships with Terraform to deploy the service on **Amazon ECS Fargate with FARGATE_SPOT capacity** behind an ALB, with VPC/NAT, ECR, CloudWatch and IAM (Bedrock-ready).

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # llm_provider = "bedrock" (or "openai")
terraform init && terraform apply
```

See [`infra/terraform/README.md`](infra/terraform/README.md) for the full walkthrough (image push, verification, teardown).

## Deploy on Amazon Bedrock AgentCore Runtime

For a fully managed alternative to Fargate — per-session microVM isolation, built-in
identity and OpenTelemetry observability — the same agent serves on **AgentCore
Runtime** via `app/runtime/agentcore_app.py`. Both paths run the identical
`AgentPipeline`, so behaviour never diverges.

```bash
uv sync --extra agentcore
agentcore configure --entrypoint app/runtime/agentcore_app.py
agentcore launch
agentcore invoke '{"prompt": "What is Kubernetes?"}'
```

Conversation memory can be backed by **AgentCore Memory** with a one-line config
change (`MEMORY_BACKEND=agentcore`), mirroring the LLM provider strategy. Full guide:
[`docs/agentcore.md`](docs/agentcore.md).

## Full-AWS RAG: Amazon S3 Vectors + Nova + Titan

Set `VECTOR_BACKEND=s3_vectors` to store embeddings in **Amazon S3 Vectors** — a
purpose-built, serverless vector store managed entirely via SDK (no console, no
OpenSearch/Aurora cluster). Paired with **Amazon Nova** for generation (via the
Converse API, with Nova Micro ↔ Nova Pro tiering) and **Amazon Titan Text Embeddings
V2** for embeddings, it makes the whole stack native AWS. The `S3VectorStore` keeps
the same `VectorStore` contract, so the agent code is unchanged. Full guide:
[`docs/rag-s3-vectors.md`](docs/rag-s3-vectors.md).

```env
LLM_PROVIDER=bedrock
BEDROCK_MODEL_ID=us.amazon.nova-pro-v1:0
EMBEDDING_PROVIDER=bedrock
VECTOR_BACKEND=s3_vectors
S3_VECTORS_BUCKET=genai-agents-vectors
```

## Tech Stack

FastAPI · LangGraph · Amazon Nova · Amazon Titan Embeddings · **Amazon S3 Vectors** · AWS Bedrock · **AgentCore (Runtime + Memory)** · OpenAI · Docker · ECS Fargate · Terraform · GitHub Actions · pytest
