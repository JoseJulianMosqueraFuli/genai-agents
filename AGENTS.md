# genai-agents

FastAPI + LangGraph platform that answers questions grounded on your documents (RAG), with guardrails, evaluation and cost tracking. Development is TDD: write the failing test first, then implement.

## Commands

- Run API: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Tests: `pytest tests/ -v` (25 tests, all providers mocked — no `.env` or network needed)
- Docker: `docker compose up --build` (API at `:8000`); tests via `docker compose run --rm test-api`
- CI: pushes/PRs to `main` run `.github/workflows/ci.yml` (pip install + pytest)

## Environment

- Config lives in `app/config.py` (pydantic-settings), loaded from `.env`.
- Provider selection: `LLM_PROVIDER=openai|bedrock`. Runtime needs `OPENAI_API_KEY` or AWS credentials; tests don't.
- Guardrails toggle: `ENABLE_GUARDRAILS`.
- No lint/typecheck/formatter configured; `pytest` is the only verification gate.

## Architecture notes

- `app/providers/` — `LLMProvider` ABC (`generate`, `embed`). `OpenAIProvider` (chat + embeddings) and `BedrockProvider` (Claude). Factory in `providers/factory.py`.
- `app/rag/retriever.py` — in-memory `VectorStore` (embed documents, cosine search, top-k). Swap for pgvector/FAISS later.
- `app/agents/` — LangGraph `StateGraph`: `retrieve` → `answer`. Nodes in `nodes.py`, state schema in `state.py`.
- `app/guards/` — input guard (prompt injection + PII scan) and output guard (PII redaction). `guards/__init__.py` exposes `inspect_input` / `inspect_output`.
- `app/eval/` — `metrics.py` (faithfulness, answer relevance), `cost.py` (`CostTracker`).
- `app/main.py` — FastAPI wiring: guardrail → graph → guardrail → eval → cost → JSON. Provider instantiated once at import; patched in tests via monkeypatching.

## Test quirks

- `tests/test_guards.py` regex-based; keep PII patterns in `app/guards/pii.py`.
- `tests/test_graph.py` uses `FakeProvider` (deterministic embeds + responses) — do not hit real APIs in tests.
- When adding metrics, keep thresholds explicit per test; metrics are intentionally simple heuristics (RAGAS is the roadmap).
