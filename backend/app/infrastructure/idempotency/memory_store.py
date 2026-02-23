import time
from typing import Dict, Optional

class InMemoryIdempotencyStore:
    """Store in-memory per test mode con rudimentale TTL management."""
    def __init__(self, ttl_seconds: int = 3600):
        self._store: Dict[str, dict] = {}
        self.ttl = ttl_seconds
        
    async def check_and_set(self, key: str, payload: dict) -> bool:
        """Controlla se esiste e non è scaduto, altrimenti salva."""
        now = time.time()
        
        # Pulizia lazy delle chiavi scadute
        expired_keys = [k for k, v in self._store.items() if now - v.get('timestamp', 0) > self.ttl]
        for k in expired_keys:
            del self._store[k]
            
        if key in self._store:
            return False
            
        self._store[key] = {
            'payload': payload,
            'timestamp': now
        }
        return True
