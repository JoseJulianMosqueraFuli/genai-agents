# GenAI Agents

[![CI](https://github.com/JoseJulianMosqueraFuli/genai-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/JoseJulianMosqueraFuli/genai-agents/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](README.md) | Español

Plataforma de agentes GenAI de nivel producción sobre **AWS Bedrock**: **RAG** (generación aumentada por recuperación) + generación con **Amazon Nova** + embeddings **Titan v2** + orquestación con **LangGraph** + **guardrails** (redacción de PII, defensa contra prompt injection) + **evaluación** (faithfulness, relevancia de respuesta) + **tracking de costos** — detrás de un servicio FastAPI, containerizado y con CI.

## ¿Por qué este proyecto?

La mayoría de demos GenAI se quedan en "llamar a un LLM". Este está construido como un servicio de producción:

- **AWS Bedrock vía Converse API** detrás de una interfaz de proveedor — agnóstico de modelo (Amazon Nova por defecto, también Claude/Llama) y sin claves de API de terceros.
- **Pipeline RAG** con búsqueda vectorial sobre tus documentos (embeddings + similitud coseno).
- **Agente LangGraph** conectando recuperación → grounding → respuesta, para que cada respuesta sea trazable.
- **Guardrails** de entrada (prompt injection) y salida (redacción de PII) — requerido para clientes reales.
- **Eval + observabilidad**: puntajes de faithfulness / relevancia y costo por request en USD.
- **TDD**: 64 tests, todos los proveedores mockeados — CI los corre en cada push.

## Arquitectura

```
 User query
     │
     ▼
[Guardrails: entrada] ──bloqueado?──► 403
     │ permitido
     ▼
[Agente LangGraph]
   retrieve ──► embed query ──► búsqueda vectorial ──► top-k chunks
     │
     ▼
   answer ──► LLM (AWS Bedrock: Amazon Nova) fundamentado en contexto
     │
     ▼
[Guardrails: salida] ── redacción de PII
     │
     ▼
[Eval: faithfulness + relevancia] ──► [Tracking de costos (USD)]
     │
     ▼
  Respuesta JSON
```

## Inicio rápido

```bash
cp .env.example .env   # configura región/modelo; las credenciales vienen de la cadena AWS
uv sync                # crea .venv desde pyproject.toml + uv.lock
uv run uvicorn app.main:app --reload
```

> Usa [uv](https://docs.astral.sh/uv/) para gestionar dependencias. Instálalo con
> `curl -LsSf https://astral.sh/uv/install.sh | sh` (o `pipx install uv`).

```bash
curl -s http://localhost:8000/v1/agents/chat \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is Kubernetes?"}'
```

### Docker

```bash
docker compose -f docker/docker-compose.yml up --build
# API → http://localhost:8000   health → /health
```

### Tests

```bash
docker compose -f docker/docker-compose.yml run --rm test-api   # o:
uv run pytest tests/ -v
```

## API

### `POST /v1/agents/chat`

```json
{ "query": "What is Kubernetes?", "use_rag": true }
```

```json
{
  "query": "What is Kubernetes?",
  "answer": "Kubernetes is a container orchestration platform...",
  "provider": "bedrock",
  "model": "us.amazon.nova-pro-v1:0",
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
  "provider": "bedrock",
  "guardrails": true
}
```

## Roadmap

- [ ] Vector store persistente (pgvector / FAISS) en lugar de en memoria
- [ ] Evaluación con métricas estilo RAGAS y dataset de regresión
- [ ] Enrutamiento A/B de modelos y canary deployments
- [ ] Políticas guardrail como código (topes de presupuesto, allowlists)
- [ ] Métricas Prometheus para latencia, costos y drift de eval

## Despliegue en AWS (ECS Fargate Spot)

El proyecto incluye Terraform para desplegar el servicio en **Amazon ECS Fargate con capacidad FARGATE_SPOT** detrás de un ALB, con VPC/NAT, ECR, CloudWatch e IAM (listo para Bedrock).

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # configura región + ids de modelo Bedrock
terraform init && terraform apply
```

Mira [`infra/terraform/README.md`](infra/terraform/README.md) para el paso a paso completo (push de imagen, verificación, teardown).

## Stack

FastAPI · LangGraph · Amazon Nova · Amazon Titan Embeddings · AWS Bedrock · Docker · ECS Fargate · Terraform · GitHub Actions · pytest
