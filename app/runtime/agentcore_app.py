"""Amazon Bedrock AgentCore Runtime entrypoint.

State of the art on AWS for *serving* agents. Instead of operating your own
container + ALB + autoscaling (the ECS Fargate path in `infra/terraform`),
AgentCore Runtime gives you:

- per-session microVM isolation and session affinity (warm across turns),
- fast cold starts and extended (async) runtimes,
- built-in identity and OAuth,
- OpenTelemetry traces to CloudWatch out of the box (ADOT).

You expose a single ``invoke(payload)`` entrypoint and the platform owns the HTTP
server (``/invocations`` POST + ``/ping`` GET), scaling and routing.

This module reuses the shared :class:`app.pipeline.AgentPipeline`, so a turn behaves
identically whether it is served by FastAPI (ECS Fargate, ``app/main.py``) or by
AgentCore Runtime. The pipeline is created lazily so this module stays importable in
CI/tests without an LLM key or the ``bedrock-agentcore`` SDK installed.

Run locally / in the AgentCore container::

    python -m app.runtime.agentcore_app        # SDK starts the HTTP server on :8080

Deploy with the starter toolkit (see docs/agentcore.md)::

    agentcore configure --entrypoint app/runtime/agentcore_app.py
    agentcore launch
"""

from __future__ import annotations

from typing import Any

from app.logging_config import structured_log
from app.pipeline import AgentPipeline

try:  # SDK is only required to actually serve on AgentCore Runtime.
    from bedrock_agentcore.runtime import BedrockAgentCoreApp
except ImportError:  # pragma: no cover - exercised only when SDK is absent
    BedrockAgentCoreApp = None  # type: ignore[assignment]


_pipeline: AgentPipeline | None = None


def get_pipeline() -> AgentPipeline:
    """Lazily build the shared pipeline (avoids provider init at import time)."""
    global _pipeline
    if _pipeline is None:
        _pipeline = AgentPipeline()
    return _pipeline


def _resolve_session_id(payload: dict, context: Any) -> str:
    # AgentCore injects a session id on the runtime context; prefer it so memory
    # keys line up with the platform's per-session microVM.
    for attr in ("session_id", "runtime_session_id"):
        value = getattr(context, attr, None)
        if value:
            return str(value)
    return str(payload.get("session_id") or "default")


async def handle(payload: dict, context: Any = None) -> dict:
    """Core entrypoint logic. Pure and testable — no SDK required.

    Accepts the AgentCore invocation payload and returns a JSON-serializable dict.
    ``prompt`` is the AgentCore convention; ``query`` is accepted for parity with
    the FastAPI endpoint.
    """
    payload = payload or {}
    query = (payload.get("prompt") or payload.get("query") or "").strip()
    if not query:
        return {"error": "payload must include a non-empty 'prompt' (or 'query')"}

    use_rag = bool(payload.get("use_rag", True))
    session_id = _resolve_session_id(payload, context)

    structured_log("INFO", "agentcore.invoke", query_len=len(query), session_id=session_id)
    result = await get_pipeline().run(query, use_rag=use_rag, session_id=session_id)
    return result.to_dict()


def build_app():
    """Construct the AgentCore Runtime app. Requires the ``bedrock-agentcore`` SDK."""
    if BedrockAgentCoreApp is None:
        raise RuntimeError(
            "AgentCore Runtime requires the 'bedrock-agentcore' package. "
            "Install it with: uv sync --extra agentcore"
        )

    app = BedrockAgentCoreApp()

    @app.entrypoint
    async def invoke(payload, context=None):  # pragma: no cover - thin SDK glue
        return await handle(payload, context)

    return app


if __name__ == "__main__":  # pragma: no cover - container entrypoint
    build_app().run()
