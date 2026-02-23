"""
Idempotency Middleware for AI-Trading-Bot
SOTA 2026 Consistency Logic

This module implements idempotency to prevent duplicate operations in financial transactions.
It uses a Token-based approach where clients provide a unique `Idempotency-Key` header.

Logic:
1. Check for `Idempotency-Key` header.
2. If present, check Cache (Redis/Memory) for existing result.
3. If cached, return stored response immediately (no re-execution).
4. If not cached, execute request and cache the response.
"""

from typing import Optional, Dict, Any
import logging
import json
import time

logger = logging.getLogger(__name__)

# Basic In-Memory Cache for MVP (Upgrade to Redis in later phase)
_memory_cache: Dict[str, Dict[str, Any]] = {}

class IdempotencyLayer:
    def __init__(self, ttl_seconds: int = 86400):
        self.ttl = ttl_seconds

    async def process(self, key: str, operation_func, *args, **kwargs):
        """
        Execute an operation idempotently.
        
        Args:
            key (str): Unique idempotency key.
            operation_func (callable): The async function to execute.
        """
        if not key:
            # Bypass if no key provided
            return await operation_func(*args, **kwargs)

        # 1. Check Cache
        cached = self._get_from_cache(key)
        if cached:
            logger.info(f"Idempotency Hit: Returning cached result for {key}")
            return cached['result']

        # 2. Execute Operation
        result = await operation_func(*args, **kwargs)

        # 3. Cache Result
        self._set_to_cache(key, result)
        return result

    def _get_from_cache(self, key: str) -> Optional[Dict]:
        entry = _memory_cache.get(key)
        if not entry:
            return None
        
        if time.time() > entry['expiry']:
            del _memory_cache[key]
            return None
            
        return entry

    def _set_to_cache(self, key: str, result: Any):
        _memory_cache[key] = {
            'result': result,
            'expiry': time.time() + self.ttl
        }
