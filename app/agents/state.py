from typing import TypedDict


class AgentState(TypedDict, total=False):
    query: str
    context: str
    history: str
    session_id: str
    answer: str
    claims: list[str]
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    guardrail_blocked: bool
    error: str
