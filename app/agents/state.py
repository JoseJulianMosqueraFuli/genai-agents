from typing import List, TypedDict


class AgentState(TypedDict, total=False):
    query: str
    context: str
    answer: str
    claims: List[str]
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    guardrail_blocked: bool
    error: str
