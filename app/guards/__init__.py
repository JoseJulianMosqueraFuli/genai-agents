from app.config import get_settings
from app.guards import injection, pii
from app.guards.base import GuardrailResult


def inspect_input(text: str) -> GuardrailResult:
    """Run all input guardrails and aggregate results."""
    settings = get_settings()
    if not settings.enable_guardrails:
        return GuardrailResult(allowed=True)

    reasons: list[str] = []
    for check in (injection.check, pii.check):
        result = check(text)
        reasons.extend(result.reasons)

    return GuardrailResult(allowed=not reasons, reasons=reasons)


def inspect_output(text: str) -> tuple[GuardrailResult, str]:
    """Sanitize model output before returning it to the user.

    Returns (result, sanitized_text) so the caller can replace the answer
    with the redacted version.
    """
    settings = get_settings()
    if not settings.enable_guardrails:
        return GuardrailResult(allowed=True), text

    result = pii.check(text, redact=True)
    sanitized = pii.redact_pii(text) if result.reasons else text
    return result, sanitized
