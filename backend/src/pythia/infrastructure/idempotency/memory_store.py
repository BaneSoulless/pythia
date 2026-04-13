import time
from collections.abc import Callable
from typing import Any


class InMemoryIdempotencyStore:
    """Store in-memory per test mode con rudimentale TTL management."""

    def __init__(self, ttl_seconds: int = 3600):
        self._store: dict[str, dict] = {}
        self.ttl = ttl_seconds

    async def check_and_set(self, key: str, payload: dict) -> bool:
        """Controlla se esiste e non è scaduto, altrimenti salva."""
        now = time.time()

        # Pulizia lazy delle chiavi scadute
        expired_keys = [
            k for k, v in self._store.items() if now - v.get("timestamp", 0) > self.ttl
        ]
        for k in expired_keys:
            del self._store[k]

        if key in self._store:
            return False

        self._store[key] = {"payload": payload, "timestamp": now}
        return True


class IdempotencyLayer:
    """Idempotency layer ensuring operations execute at most once per key."""

    def __init__(self, ttl_seconds: int = 3600):
        self._results: dict[str, Any] = {}
        self._store = InMemoryIdempotencyStore(ttl_seconds)

    async def process(
        self, key: str, func: Callable, *args: Any, **kwargs: Any
    ) -> Any:
        """Execute func only if key hasn't been processed before."""
        if key in self._results:
            return self._results[key]
        result = await func(*args, **kwargs)
        self._results[key] = result
        return result

