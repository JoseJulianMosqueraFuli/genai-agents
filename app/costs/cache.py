import hashlib
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    created_at: float
    ttl_seconds: int

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds


class ResponseCache:
    """In-memory cache for agent responses.

    Cost discipline: identical queries shouldn't hit the LLM twice. This is
    the "caching" part of the cost discipline Provectus asks about.
    """

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0

    def _key(self, query: str, model: str) -> str:
        return hashlib.sha256(f"{model}::{query.strip().lower()}".encode()).hexdigest()

    def get(self, query: str, model: str) -> Any | None:
        key = self._key(query, model)
        entry = self._store.get(key)
        if entry is None:
            self.misses += 1
            return None
        if entry.is_expired:
            del self._store[key]
            self.misses += 1
            return None
        self.hits += 1
        return entry.value

    def set(self, query: str, model: str, value: Any) -> None:
        key = self._key(query, model)
        self._store[key] = CacheEntry(
            value=value, created_at=time.time(), ttl_seconds=self.ttl_seconds
        )

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {
            "size": len(self._store),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 3) if total else 0.0,
        }

    def clear(self) -> None:
        self._store.clear()
