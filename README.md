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
pip install -r requirements.txt
uvicorn app.main:app --reload
```

```bash
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
pytest tests/ -v
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
- [ ] Persistent vector store (pgvector / FAISS) instead of in-memory
- [ ] Evaluation with RAGAS-style metrics and a regression dataset
- [ ] Model A/B routing and canary deployments
- [ ] Guardrail-as-code policies (budget caps, topic allowlists)
- [ ] AgentCore Gateway (expose tools as MCP) + AgentCore Identity
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
pip install -r requirements.txt -r requirements-agentcore.txt
agentcore configure --entrypoint app/runtime/agentcore_app.py
agentcore launch
agentcore invoke '{"prompt": "What is Kubernetes?"}'
```

Conversation memory can be backed by **AgentCore Memory** with a one-line config
change (`MEMORY_BACKEND=agentcore`), mirroring the LLM provider strategy. Full guide:
[`docs/agentcore.md`](docs/agentcore.md).

## Tech Stack

FastAPI · LangGraph · OpenAI · AWS Bedrock · **AgentCore (Runtime + Memory)** · Docker · ECS Fargate · Terraform · GitHub Actions · pytest
