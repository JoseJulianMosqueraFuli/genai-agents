import time

from app.costs.cache import ResponseCache
from app.costs.tiering import ComplexityRouter


class TestComplexityRouter:
    def test_short_factual_goes_cheap(self):
        r = ComplexityRouter()
        d = r.decide("What is Kubernetes?")
        assert d.tier == "cheap"
        assert "nova-micro" in d.model

    def test_reasoning_goes_strong(self):
        r = ComplexityRouter()
        d = r.decide("Explain why and compare these two architectures step by step")
        assert d.tier == "strong"
        assert "strong" in d.reason or "reasoning" in d.reason.lower()

    def test_design_goes_strong(self):
        r = ComplexityRouter()
        d = r.decide("Design a scalable microservices architecture for this use case")
        assert d.tier == "strong"


class TestResponseCache:
    def test_get_miss_then_hit(self):
        c = ResponseCache(ttl_seconds=3600)
        assert c.get("what is k8s?", "nova-micro") is None
        c.set("what is k8s?", "nova-micro", "answer")
        assert c.get("what is k8s?", "nova-micro") == "answer"

    def test_expired_returns_none(self):
        c = ResponseCache(ttl_seconds=1)
        c.set("q", "m", "a")
        time.sleep(1.1)
        assert c.get("q", "m") is None

    def test_different_models_different_keys(self):
        c = ResponseCache()
        c.set("q", "cheap-model", "a")
        assert c.get("q", "strong-model") is None

    def test_stats_track_hits(self):
        c = ResponseCache()
        c.set("q", "m", "a")
        c.get("q", "m")
        c.get("q", "m")
        s = c.stats()
        assert s["hits"] == 2
        assert s["misses"] == 0
