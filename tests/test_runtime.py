"""Tests for the Amazon Bedrock AgentCore Runtime entrypoint.

No network, no AWS, no `bedrock-agentcore` SDK: we exercise the pure `handle()`
logic with a fake pipeline, mirroring the FakeProvider pattern used elsewhere.
"""

import pytest

from app.pipeline import AgentResult
from app.runtime import agentcore_app


class FakePipeline:
    """Deterministic stand-in for AgentPipeline; records the last call."""

    def __init__(self):
        self.calls = []

    async def run(
        self, query: str, use_rag: bool = True, session_id: str = "default"
    ) -> AgentResult:
        self.calls.append({"query": query, "use_rag": use_rag, "session_id": session_id})
        return AgentResult(
            query=query,
            answer="grounded answer",
            provider="fake",
            model="fake-model",
            session_id=session_id,
        )


class FakeContext:
    def __init__(self, session_id: str):
        self.session_id = session_id


@pytest.fixture
def fake_pipeline(monkeypatch):
    fake = FakePipeline()
    monkeypatch.setattr(agentcore_app, "get_pipeline", lambda: fake)
    return fake


@pytest.mark.asyncio
async def test_handle_returns_serializable_result(fake_pipeline):
    result = await agentcore_app.handle({"prompt": "What is Kubernetes?"})
    assert result["answer"] == "grounded answer"
    assert result["provider"] == "fake"
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_handle_accepts_query_alias(fake_pipeline):
    await agentcore_app.handle({"query": "hello", "use_rag": False})
    assert fake_pipeline.calls[-1]["query"] == "hello"
    assert fake_pipeline.calls[-1]["use_rag"] is False


@pytest.mark.asyncio
async def test_handle_rejects_empty_prompt(fake_pipeline):
    result = await agentcore_app.handle({"prompt": "   "})
    assert "error" in result
    assert fake_pipeline.calls == []


@pytest.mark.asyncio
async def test_runtime_context_session_overrides_payload(fake_pipeline):
    await agentcore_app.handle(
        {"prompt": "hi", "session_id": "from-payload"}, FakeContext("from-runtime")
    )
    assert fake_pipeline.calls[-1]["session_id"] == "from-runtime"


@pytest.mark.asyncio
async def test_session_falls_back_to_payload_then_default(fake_pipeline):
    await agentcore_app.handle({"prompt": "a", "session_id": "s1"}, context=None)
    assert fake_pipeline.calls[-1]["session_id"] == "s1"

    await agentcore_app.handle({"prompt": "b"}, context=None)
    assert fake_pipeline.calls[-1]["session_id"] == "default"


def test_build_app_requires_sdk(monkeypatch):
    monkeypatch.setattr(agentcore_app, "BedrockAgentCoreApp", None)
    with pytest.raises(RuntimeError, match="bedrock-agentcore"):
        agentcore_app.build_app()
