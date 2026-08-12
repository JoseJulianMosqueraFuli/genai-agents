import re
from dataclasses import dataclass
from typing import List

_STOPWORDS = {"the", "a", "an", "is", "are", "of", "to", "in", "and", "or", "for", "with", "on", "at"}


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS}


@dataclass
class EvalResult:
    metric: str
    score: float
    passed: bool
    threshold: float


def faithfulness(claims: List[str], context: str) -> float:
    """Fraction of model claims whose content words appear in the retrieved context."""
    if not claims:
        return 0.0
    context_tokens = _tokens(context)
    if not context_tokens:
        return 0.0
    grounded = 0
    for claim in claims:
        claim_tokens = _tokens(claim)
        if not claim_tokens:
            continue
        overlap = claim_tokens & context_tokens
        if overlap:
            grounded += 1
    return grounded / len(claims)


def answer_relevance(answer: str, query: str) -> float:
    """Lexical overlap between answer and query content words."""
    query_tokens = _tokens(query)
    if not query_tokens:
        return 1.0
    answer_tokens = _tokens(answer)
    if not answer_tokens:
        return 0.0
    overlap = query_tokens & answer_tokens
    return len(overlap) / len(query_tokens)


def evaluate_answer(answer: str, query: str, context: str, claims: List[str], threshold: float = 0.7) -> List[EvalResult]:
    f = faithfulness(claims, context)
    r = answer_relevance(answer, query)
    return [
        EvalResult(metric="faithfulness", score=f, passed=f >= threshold, threshold=threshold),
        EvalResult(metric="answer_relevance", score=r, passed=r >= threshold, threshold=threshold),
    ]
