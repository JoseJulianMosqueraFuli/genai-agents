from app.agents.state import AgentState
from app.config import get_settings
from app.logging_config import structured_log
from app.providers.base import LLMProvider


RETRIEVE_SYSTEM = (
    "You are a retrieval specialist. Given a question, rewrite it into a compact, "
    "search-friendly query that captures the user's intent for a vector database."
)

ANSWER_SYSTEM = (
    "You are a helpful assistant. Answer strictly using the provided context. "
    "If the context does not contain the answer, say you don't know. "
    "Never invent facts. Be concise."
)


class Router:
    """Determines which path the agent should take for a given query."""

    def decide(self, query: str, context: str) -> str:
        if not context.strip():
            return "answer_without_context"
        return "answer_with_context"


class RetrieverNode:
    def __init__(self, provider: LLMProvider, store) -> None:
        self.provider = provider
        self.store = store

    async def run(self, state: AgentState) -> AgentState:
        query = state["query"]
        rewritten = await self._rewrite_query(query)
        docs = await self.store.search(rewritten)
        context = "\n\n".join(f"[{d.chunk_id}] {d.text}" for d in docs)
        state["context"] = context
        return state

    async def _rewrite_query(self, query: str) -> str:
        settings = get_settings()
        if settings.llm_provider == "openai":
            return query
        resp = await self.provider.generate(RETRIEVE_SYSTEM, query, max_tokens=80)
        return resp.text.strip() or query


class AnswerNode:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def run(self, state: AgentState) -> AgentState:
        query = state["query"]
        context = state.get("context", "")
        system = ANSWER_SYSTEM
        user = f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
        resp = await self.provider.generate(system, user)
        state["answer"] = resp.text
        state["provider"] = self.provider.name
        state["model"] = resp.model
        state["input_tokens"] = resp.usage.input_tokens
        state["output_tokens"] = resp.usage.output_tokens
        structured_log(
            "INFO",
            "agent.answer",
            provider=self.provider.name,
            model=resp.model,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )
        return state
