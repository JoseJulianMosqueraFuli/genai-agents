import json
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.eval.metrics import answer_relevance, faithfulness


def load_eval_dataset() -> list[dict]:
    path = Path(__file__).resolve().parent / "dataset" / "qa.json"
    with open(path) as f:
        return json.load(f)["questions"]


class EvalRunner:
    """Runs the eval dataset through an answerer callable and measures quality.

    In CI, the answerer is the real agent; in unit tests it's a mock.
    The release gate (below) is what decides promotion.
    """

    def __init__(self, answerer: Callable[[str], Awaitable[str]] | None = None):
        self.answerer = answerer or self._echo_answerer

    @staticmethod
    async def _echo_answerer(query: str) -> str:
        """Placeholder for tests; returns the query (not a real LLM call)."""
        return query

    async def run(self, dataset: list[dict]) -> list[dict]:
        results = []
        for item in dataset:
            answer = await self.answerer(item["query"])
            results.append(
                {
                    "id": item["id"],
                    "query": item["query"],
                    "expected": item["expected"],
                    "answer": answer,
                    "faithfulness": faithfulness([item["expected"]], answer),
                    "relevance": answer_relevance(answer, item["query"]),
                    "category": item["category"],
                }
            )
        return results


class ReleaseGate:
    """Aggregate thresholds that a candidate must pass before promotion.

    This is the 'what gated a release' part: metrics + thresholds + pass/fail.
    """

    def __init__(self, min_faithfulness: float = 0.6, min_relevance: float = 0.5):
        self.min_faithfulness = min_faithfulness
        self.min_relevance = min_relevance

    def evaluate(self, results: list[dict]) -> dict:
        avg_f = sum(r["faithfulness"] for r in results) / len(results)
        avg_r = sum(r["relevance"] for r in results) / len(results)
        per_category = {}
        for r in results:
            cat = r["category"]
            per_category.setdefault(cat, []).append(r)

        return {
            "avg_faithfulness": round(avg_f, 3),
            "avg_relevance": round(avg_r, 3),
            "thresholds": {
                "faithfulness": self.min_faithfulness,
                "relevance": self.min_relevance,
            },
            "passed": avg_f >= self.min_faithfulness and avg_r >= self.min_relevance,
            "per_category": {
                cat: {
                    "count": len(items),
                    "avg_faithfulness": round(
                        sum(i["faithfulness"] for i in items) / len(items), 3
                    ),
                }
                for cat, items in per_category.items()
            },
            "num_questions": len(results),
        }
