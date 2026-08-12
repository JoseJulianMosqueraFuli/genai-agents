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

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | `openai` or `bedrock` |
| `LLM_MODEL` | `gpt-4o-mini` | Model for OpenAI |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-5-sonnet-20240620-v1` | Claude via Bedrock |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embeddings model |
| `ENABLE_GUARDRAILS` | `true` | Toggle input/output guards |
| `COST_PER_1K_INPUT_TOKENS` | `0.00015` | $/1k input tokens (cost model) |
| `COST_PER_1K_OUTPUT_TOKENS` | `0.0006` | $/1k output tokens (cost model) |

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
{ "status": "ok", "app": "genai-agents", "provider": "openai", "guardrails": true }
```

## Roadmap

- [ ] Persistent vector store (pgvector / FAISS) instead of in-memory
- [ ] Evaluation with RAGAS-style metrics and a regression dataset
- [ ] Model A/B routing and canary deployments
- [ ] Guardrail-as-code policies (budget caps, topic allowlists)
- [ ] Prometheus metrics for latency, cost and eval drift

## Deploy on AWS (ECS Fargate Spot)

The project ships with Terraform to deploy the service on **Amazon ECS Fargate with FARGATE_SPOT capacity** behind an ALB, with VPC/NAT, ECR, CloudWatch and IAM (Bedrock-ready).

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # llm_provider = "bedrock" (or "openai")
terraform init && terraform apply
```

See [`infra/terraform/README.md`](infra/terraform/README.md) for the full walkthrough (image push, verification, teardown).

## Tech Stack

FastAPI · LangGraph · OpenAI · AWS Bedrock · Docker · ECS Fargate · Terraform · GitHub Actions · pytest
