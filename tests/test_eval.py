import pytest

from app.agents.nodes import Router
from app.agents.state import AgentState
from app.eval.cost import CostTracker
from app.eval.metrics import answer_relevance, evaluate_answer, faithfulness
from app.providers.base import LLMUsage


class TestRouter:
    def test_with_context(self):
        r = Router()
        assert r.decide("q", "some context here") == "answer_with_context"

    def test_without_context(self):
        r = Router()
        assert r.decide("q", "  ") == "answer_without_context"


class TestCostTracker:
    def test_accumulates_usage(self):
        tracker = CostTracker(input_price_per_1k=0.15, output_price_per_1k=0.60)
        tracker.add(LLMUsage(input_tokens=1000, output_tokens=1000))
        tracker.add(LLMUsage(input_tokens=500, output_tokens=500))
        est = tracker.estimate()
        assert est.input_tokens == 1500
        assert est.output_tokens == 1500
        assert est.total == pytest.approx(0.15 * 1.5 + 0.60 * 1.5)

    def test_request_count(self):
        tracker = CostTracker()
        assert tracker.request_count == 0
        tracker.add(LLMUsage(1, 1))
        assert tracker.request_count == 1


class TestMetrics:
    def test_faithfulness_grounded_claims(self):
        assert faithfulness(["Kubernetes orchestrates containers"], "Kubernetes orchestrates containers and scales them") == 1.0

    def test_faithfulness_hallucination(self):
        assert faithfulness(["The moon is made of cheese"], "Kubernetes docs") == 0.0

    def test_answer_relevance_overlap(self):
        assert answer_relevance("Kubernetes is a container orchestrator", "What is Kubernetes?") >= 0.5

    def test_evaluate_answer_returns_metrics(self):
        results = evaluate_answer("K8s orchestrates", "What is Kubernetes?", "K8s orchestrates containers", ["K8s orchestrates"])
        assert {r.metric for r in results} == {"faithfulness", "answer_relevance"}
