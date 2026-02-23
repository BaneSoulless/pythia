"""
Idempotency checking tramite Redis.
"""
import redis.asyncio as redis
from typing import Optional
from fastapi import Request, HTTPException
import json
import hashlib

LUA_IDEMPOTENCY_SCRIPT = """
if redis.call("EXISTS", KEYS[1]) == 1 then
    return 0
else
    redis.call("SET", KEYS[1], ARGV[1], "EX", ARGV[2])
    return 1
end
"""

class IdempotencyStore:
    """Implementa uno store di idempotenza usando script Lua in Redis."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/1"):
        self.redis_client = redis.from_url(redis_url)
        self.ttl_seconds = 86400  # 24 hours default
        self._set_if_not_exists = self.redis_client.register_script(LUA_IDEMPOTENCY_SCRIPT)
        
    async def check_and_set(self, idempotency_key: str, payload: dict) -> bool:
        """
        Controlla la chiave. Se nuova, la salva col payload e ritorna True.
        Se esistente, ritorna False (duplicato).
        """
        if not idempotency_key:
            return False
            
        key = f"idem:{idempotency_key}"
        data = json.dumps(payload)
        
        result = await self._set_if_not_exists(keys=[key], args=[data, self.ttl_seconds])
        return bool(result)

    async def get_response(self, idempotency_key: str) -> Optional[dict]:
        """Recupera la risposta precedentemente salvata."""
        key = f"idem:{idempotency_key}"
        val = await self.redis_client.get(key)
        if val:
            return json.loads(val)
        return None

async def idempotency_middleware(request: Request, call_next):
    """Middleware FastAPI per forzare X-Idempotency-Key sulle API di trade."""
    if request.method == "POST" and "/api/trades" in request.url.path:
        idem_key = request.headers.get("X-Idempotency-Key")
        if not idem_key:
            raise HTTPException(status_code=400, detail="X-Idempotency-Key header is required")
            
        store = IdempotencyStore()
        body = await request.body()
        payload = {"body_hash": hashlib.sha256(body).hexdigest()}
        
        is_new = await store.check_and_set(idem_key, payload)
        if not is_new:
            raise HTTPException(status_code=409, detail="Idempotent request previously completed")
            
    response = await call_next(request)
    return response
