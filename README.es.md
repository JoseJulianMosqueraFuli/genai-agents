# GenAI Agents

[![CI](https://github.com/JoseJulianMosqueraFuli/genai-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/JoseJulianMosqueraFuli/genai-agents/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](README.md) | Español

Plataforma de agentes GenAI de nivel producción: **RAG** (generación aumentada por recuperación) + **LLMs multi-proveedor** (OpenAI / AWS Bedrock) + orquestación con **LangGraph** + **guardrails** (redacción de PII, defensa contra prompt injection) + **evaluación** (faithfulness, relevancia de respuesta) + **tracking de costos** — detrás de un servicio FastAPI, containerizado y con CI.

## ¿Por qué este proyecto?

La mayoría de demos GenAI se quedan en "llamar a un LLM". Este está construido como un servicio de producción:

- **Estrategia multi-LLM** vía interfaz de proveedores — cambia OpenAI por Bedrock (Claude) con una variable de entorno.
- **Pipeline RAG** con búsqueda vectorial sobre tus documentos (embeddings + similitud coseno).
- **Agente LangGraph** conectando recuperación → grounding → respuesta, para que cada respuesta sea trazable.
- **Guardrails** de entrada (prompt injection) y salida (redacción de PII) — requerido para clientes reales.
- **Eval + observabilidad**: puntajes de faithfulness / relevancia y costo por request en USD.
- **TDD**: 25 tests, todos los proveedores mockeados — CI los corre en cada push.

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
   answer ──► LLM (OpenAI | Bedrock) fundamentado en contexto
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
cp .env.example .env   # llena OPENAI_API_KEY (o cambia a BEDROCK)
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
docker compose run --rm test-api        # o:
pytest tests/ -v
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

- [ ] Vector store persistente (pgvector / FAISS) en lugar de en memoria
- [ ] Evaluación con métricas estilo RAGAS y dataset de regresión
- [ ] Enrutamiento A/B de modelos y canary deployments
- [ ] Políticas guardrail como código (topes de presupuesto, allowlists)
- [ ] Métricas Prometheus para latencia, costos y drift de eval

## Stack

FastAPI · LangGraph · OpenAI · AWS Bedrock · Docker · GitHub Actions · pytest
