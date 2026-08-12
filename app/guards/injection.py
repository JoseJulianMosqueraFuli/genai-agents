from app.guards.base import GuardrailResult

_INJECTION_PATTERNS = [
    "ignore all previous instructions",
    "ignore previous instructions",
    "disregard instructions",
    "you are now",
    "pretend you are",
    "act as",
    "system prompt",
    "override",
    "reveal your instructions",
    "jailbreak",
    "what is your system prompt",
]


def check(text: str) -> GuardrailResult:
    lowered = text.lower()
    hits = [p for p in _INJECTION_PATTERNS if p in lowered]
    return GuardrailResult(allowed=not hits, reasons=[f"injection:{p}" for p in hits])
