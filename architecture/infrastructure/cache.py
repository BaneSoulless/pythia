"""
Infrastructure Layer - Redis Cache
Persistence: Hot-State
"""
import redis
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("RedisCache")

class StateCache:
    """
    High-speed, persistent Hot-State Cache using Redis.
    Replaces volatile in-memory collections.
    """
    def __init__(self, host: str = 'redis', port: int = 6379, db: int = 0):
        # 'redis' hostname resolves in Docker, fallback to localhost for local
        try:
            self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
            self.client.ping()
            logger.info(f"Connected to Redis at {host}:{port}")
        except redis.ConnectionError:
            logger.warning(f"Redis connection failed at {host}. Attempting localhost...")
            try:
                self.client = redis.Redis(host='localhost', port=port, db=db, decode_responses=True)
                self.client.ping()
                logger.info("Connected to Redis at localhost")
            except Exception as e:
                logger.error(f"CRITICAL: Redis unavailable. State persistence disabled. {e}")
                self.client = None

    def push_candle(self, symbol: str, candle: Dict[str, Any], limit: int = 1000):
        """Push candle to list and trim."""
        if not self.client: return
        try:
            key = f"market_data:{symbol}"
            # Push to HEAD (Left) - Newest first approach or TAIL (Right)?
            # Usually appending to time series: RPUSH (Right)
            self.client.rpush(key, json.dumps(candle))
            self.client.ltrim(key, -limit, -1) # Keep last 'limit' items
        except Exception as e:
            logger.error(f"Cache Write Error: {e}")

    def get_history(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get last N candles."""
        if not self.client: return []
        try:
            key = f"market_data:{symbol}"
            # Return last N items
            items = self.client.lrange(key, -limit, -1)
            return [json.loads(i) for i in items]
        except Exception as e:
            logger.error(f"Cache Read Error: {e}")
            return []
