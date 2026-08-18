import re

from app.guards.base import GuardrailResult

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?(?:\(\d{2,4}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)"
)
CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def scan_pii(text: str) -> list[str]:
    hits: list[str] = []
    if EMAIL_RE.search(text):
        hits.append("email")
    if PHONE_RE.search(text):
        hits.append("phone")
    if CREDIT_CARD_RE.search(text):
        hits.append("credit_card")
    if SSN_RE.search(text):
        hits.append("ssn")
    return hits


def redact_pii(text: str) -> str:
    redacted = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    redacted = PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    redacted = CREDIT_CARD_RE.sub("[REDACTED_CARD]", redacted)
    redacted = SSN_RE.sub("[REDACTED_SSN]", redacted)
    return redacted


def check(text: str, redact: bool = False) -> GuardrailResult:
    hits = scan_pii(text)
    if redact and hits:
        text = redact_pii(text)
    reasons = [f"pii:{h}" for h in hits]
    return GuardrailResult(allowed=not hits, reasons=reasons)
