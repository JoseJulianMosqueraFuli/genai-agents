# genai-agents

FastAPI + LangGraph platform that answers questions grounded on your documents (RAG), with guardrails, evaluation and cost tracking. Development is TDD: write the failing test first, then implement.

## Commands

- Deps: **uv** (`pyproject.toml` + `uv.lock`, source of truth). `uv sync` installs runtime + dev; `uv sync --frozen` in CI. No `requirements.txt`.
- Run API (ECS Fargate path): `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Tests: `uv run pytest tests/ -v` (53 tests, all providers/SDKs mocked — no `.env` or network needed)
- Lint/format: `uv run ruff check .` + `uv run ruff format .` — **ruff is the enforced CI gate** (line-length 100, config in `pyproject.toml`). flake8 is optional local-only (`uvx flake8 app eval tests`, `.flake8`); don't add it to CI.
- Docker: files live in `docker/`. `docker compose -f docker/docker-compose.yml up --build` (API at `:8000`); tests via `docker compose -f docker/docker-compose.yml run --rm test-api`. Build context is the repo root.
- AgentCore Runtime (managed path): `uv sync --extra agentcore`, then `agentcore configure --entrypoint app/runtime/agentcore_app.py` and `agentcore launch`. Run the container locally with `python -m app.runtime.agentcore_app` (serves on :8080).
- Terraform: `terraform -chdir=infra/terraform test` (5 plan-only tests, mocked AWS provider); `terraform -chdir=infra/terraform fmt -recursive`.
- CI: pushes/PRs to `main` run `.github/workflows/ci.yml` (uv sync + pytest). Infra changes run `.github/workflows/terraform.yml` (fmt + validate + test + tflint + tfsec).

## Environment

- Config lives in `app/config.py` (pydantic-settings), loaded from `.env`.
- Single provider: AWS Bedrock (`LLM_PROVIDER=bedrock`, the only allowed value). Runtime uses the AWS credential chain (env/`~/.aws/`/IAM role) with `bedrock:InvokeModel`; tests don't need credentials (they inject fakes). `BedrockProvider` builds a boto3 client at init, so keep pipeline construction lazy in code meant to be importable in CI — build it lazily (see `app/runtime/agentcore_app.py`).
- Memory backend: `MEMORY_BACKEND=in_memory|agentcore`. `agentcore` also needs `AGENTCORE_MEMORY_ID` (+ optional `AGENTCORE_ACTOR_ID`) and the `bedrock-agentcore` SDK.
- Guardrails toggle: `ENABLE_GUARDRAILS`.
- `bedrock-agentcore` is an optional extra (`uv sync --extra agentcore`), imported lazily in `memory.py` and `runtime/agentcore_app.py` so CI/tests run without it.
- Verification gates: ruff + `pytest` + `terraform test` (infra). See Commands for lint details.

## Architecture notes

- `app/providers/` — `LLMProvider` ABC (`generate`, `embed`). `BedrockProvider` is the only implementation: **Converse API** for generation (model-agnostic: Amazon Nova by default, also Claude/Llama) and **Titan Text Embeddings V2** for `embed`. Factory in `providers/factory.py`. Full-AWS stack: Nova (gen) + Titan v2 (embed) + S3 Vectors (RAG).
- `app/rag/` — `retriever.py` in-memory `VectorStore` (embed, cosine, top-k) and `s3_vectors.py` `S3VectorStore` (Amazon S3 Vectors via `boto3.client("s3vectors")`, managed by SDK). `factory.py` picks the backend from `VECTOR_BACKEND`. Both share the same contract (`add_documents`, `search -> List[RetrievedDoc]`, `size`).
- `app/agents/` — LangGraph `StateGraph`: `retrieve` → `answer`. Nodes in `nodes.py`, state schema in `state.py`.
- `app/guards/` — input guard (prompt injection + PII scan) and output guard (PII redaction). `guards/__init__.py` exposes `inspect_input` / `inspect_output`.
- `app/eval/` — `metrics.py` (faithfulness, answer relevance), `cost.py` (`CostTracker`).
- `app/agents/memory.py` — `ConversationMemory` ABC with `InMemoryConversationMemory` (default) and `AgentCoreMemory` (Bedrock AgentCore Memory adapter). Backend chosen by `get_memory()` from config.
- `app/pipeline.py` — the single source of truth for a turn: guardrail → tiering → cache → graph → guardrail → eval → cost → memory. Both entrypoints reuse it so behaviour is identical. The tier-selected model is injected into the graph `state["model"]` and passed to `provider.generate(model=...)`, so cheap/strong routing actually reaches the LLM (not just the cache key).
- `app/main.py` — FastAPI wiring (ECS Fargate path); instantiates `AgentPipeline()` at import. Endpoints: `POST /v1/agents/chat`, `POST /v1/documents` (RAG ingestion → `AgentPipeline.ingest`, which runs `ensure_index()` once, `add_documents`, then clears the response cache), `GET /health`, `GET /v1/cache/stats`. `LLMProviderError` is mapped to a clean 502 via an exception handler.
- `app/runtime/agentcore_app.py` — Amazon Bedrock AgentCore Runtime entrypoint (`@app.entrypoint`). Reuses `AgentPipeline` via a lazy `get_pipeline()`; pure `handle()` is unit-tested without the SDK.
- `infra/terraform/` — ECS runs on **Fargate Spot** via the service's `capacity_provider_strategy` (NOT `launch_type`, which would silently bypass Spot). `fargate_base_count > 0` adds an on-demand base. `docs/agentcore.md` covers the AgentCore deployment; `docs/architecture-aws.drawio` is the full-AWS diagram.

## Test quirks

- `tests/test_guards.py` regex-based; keep PII patterns in `app/guards/pii.py`.
- `tests/test_graph.py` uses `FakeProvider` (deterministic embeds + responses) — do not hit real APIs in tests.
- `tests/test_runtime.py` monkeypatches `agentcore_app.get_pipeline` with a `FakePipeline`; the runtime entrypoint is tested without the `bedrock-agentcore` SDK or AWS.
- `tests/test_s3_vectors.py` injects a fake `s3vectors` client into `S3VectorStore`; RAG on S3 Vectors is tested without boto3 talking to AWS.
- When adding metrics, keep thresholds explicit per test; metrics are intentionally simple heuristics (RAGAS is the roadmap).
- Infra tests (`infra/terraform/tests/infra.tftest.hcl`) are plan-only with a mocked provider; assert on module outputs (e.g. `capacity_providers`) rather than internal resources.
