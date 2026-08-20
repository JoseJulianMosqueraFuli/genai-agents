# genai-agents — web UI

React + Vite + TypeScript single-page app for the genai-agents API. Chat against
`POST /v1/agents/chat` and ingest documents via `POST /v1/documents`, with a live
health indicator and per-answer metadata (tier, model, cost, latency, cache hit,
eval scores, retrieved sources).

## Develop

```bash
cd frontend
pnpm install
pnpm dev             # http://localhost:5173
```

The dev server proxies `/v1` and `/health` to the API (default
`http://localhost:8000`), so no CORS setup is needed locally. Start the backend in
another terminal:

```bash
uv run uvicorn app.main:app --reload   # from the repo root
```

Override the proxy target with `VITE_API_TARGET` if the API runs elsewhere.

## Build

```bash
pnpm build           # type-checks then bundles to dist/
pnpm preview         # serve the production build locally
```

When serving the built SPA from a different origin than the API, set
`VITE_API_BASE` to the API URL and add that origin to `CORS_ALLOW_ORIGINS` on the
backend (see `app/config.py`).

## Scripts

- `pnpm dev` — dev server with HMR
- `pnpm build` — production build (`tsc -b && vite build`)
- `pnpm preview` — preview the build
- `pnpm typecheck` — type-check without emitting

## Notes

- A fresh `session_id` (UUID) is created per page load so multi-turn memory stays
  coherent server-side.
- Answers require the backend to reach AWS Bedrock (credentials + model access).
  The UI surfaces provider errors (mapped to HTTP 502) inline in the chat.
