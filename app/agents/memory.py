"""Conversation memory for multi-turn agents.

State of the art on AWS is Amazon Bedrock AgentCore Memory: a managed store that
keeps short-term (session) and long-term (cross-session) context so agents stay
coherent without you building your own storage layer.

This module exposes a small `ConversationMemory` interface so the agent code stays
provider-agnostic:

- `InMemoryConversationMemory` — default, zero-dependency, used in tests and local dev.
- `AgentCoreMemory` — thin adapter over `bedrock_agentcore.memory` for production.

The concrete backend is chosen by config (`MEMORY_BACKEND`), so switching from local
to AgentCore Memory is a one-line env change, mirroring the provider strategy used
for LLMs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, List

from app.config import get_settings
from app.logging_config import structured_log


@dataclass
class Turn:
    role: str  # "user" | "assistant"
    content: str


class ConversationMemory(ABC):
    """Stores conversation turns keyed by session id."""

    @abstractmethod
    def append(self, session_id: str, role: str, content: str) -> None:
        """Record a single turn for a session."""

    @abstractmethod
    def history(self, session_id: str) -> List[Turn]:
        """Return the ordered turns for a session (oldest first)."""

    def render(self, session_id: str) -> str:
        """Render recent history as a plain-text block for prompting."""
        turns = self.history(session_id)
        if not turns:
            return ""
        lines = [f"{t.role.capitalize()}: {t.content}" for t in turns]
        return "\n".join(lines)


class InMemoryConversationMemory(ConversationMemory):
    """Bounded, process-local memory. Good for dev/tests; lost on restart."""

    def __init__(self, max_turns: int = 20) -> None:
        self.max_turns = max_turns
        self._store: Dict[str, Deque[Turn]] = defaultdict(lambda: deque(maxlen=max_turns))

    def append(self, session_id: str, role: str, content: str) -> None:
        self._store[session_id].append(Turn(role=role, content=content))

    def history(self, session_id: str) -> List[Turn]:
        return list(self._store.get(session_id, ()))


class AgentCoreMemory(ConversationMemory):
    """Adapter over Amazon Bedrock AgentCore Memory.

    Requires the `bedrock-agentcore` SDK and AWS credentials at runtime. The import
    is deferred so local dev and CI (which never talk to AWS) don't need the package.
    """

    def __init__(self, memory_id: str, region: str | None = None, actor_id: str = "user") -> None:
        try:
            from bedrock_agentcore.memory import MemoryClient  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised only when SDK missing
            raise RuntimeError(
                "AgentCoreMemory requires the 'bedrock-agentcore' package. "
                "Install it with: pip install bedrock-agentcore"
            ) from exc

        self.memory_id = memory_id
        self.actor_id = actor_id
        self._client = MemoryClient(region_name=region) if region else MemoryClient()

    def append(self, session_id: str, role: str, content: str) -> None:
        self._client.create_event(
            memory_id=self.memory_id,
            actor_id=self.actor_id,
            session_id=session_id,
            messages=[(content, role.upper())],
        )

    def history(self, session_id: str) -> List[Turn]:
        events = self._client.list_events(
            memory_id=self.memory_id,
            actor_id=self.actor_id,
            session_id=session_id,
        )
        turns: List[Turn] = []
        for event in events or []:
            for message in event.get("messages", []):
                turns.append(Turn(role=str(message.get("role", "user")).lower(), content=message.get("content", "")))
        return turns


_memory_singleton: ConversationMemory | None = None


def get_memory() -> ConversationMemory:
    """Return the configured conversation memory backend (singleton)."""
    global _memory_singleton
    if _memory_singleton is not None:
        return _memory_singleton

    settings = get_settings()
    backend = settings.memory_backend
    if backend == "agentcore" and settings.agentcore_memory_id:
        structured_log("INFO", "memory.backend", backend="agentcore", memory_id=settings.agentcore_memory_id)
        _memory_singleton = AgentCoreMemory(
            memory_id=settings.agentcore_memory_id,
            region=settings.bedrock_region,
        )
    else:
        structured_log("INFO", "memory.backend", backend="in_memory")
        _memory_singleton = InMemoryConversationMemory()
    return _memory_singleton


def reset_memory() -> None:
    """Clear the singleton (used by tests)."""
    global _memory_singleton
    _memory_singleton = None
