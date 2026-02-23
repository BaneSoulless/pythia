"""
Redis-based caching service for the trading bot.

Provides caching for market data, AI predictions, and other expensive operations.
"""
import redis
import pickle
import logging
from typing import Any, Optional, Callable
from functools import wraps
from pythia.core.config import settings
logger = logging.getLogger(__name__)

class CacheService:
    """Redis caching service."""

    def __init__(self):
        """Initialize Redis connection."""
        try:
            self.redis = redis.Redis(host=getattr(settings, 'REDIS_HOST', 'localhost'), port=getattr(settings, 'REDIS_PORT', 6379), db=getattr(settings, 'REDIS_DB', 0), decode_responses=False, socket_connect_timeout=5)
            self.redis.ping()
            logger.info('Redis cache service initialized successfully')
        except redis.ConnectionError as e:
            logger.warning(f'Redis connection failed: {e}. Cache will be disabled.')
            self.redis = None

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if not self.redis:
            return None
        try:
            data = self.redis.get(key)
            if data:
                return pickle.loads(data)
        except Exception as e:
            logger.error(f'Cache get error for key {key}: {e}')
        return None

    def set(self, key: str, value: Any, ttl: int=60) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis:
            return False
        try:
            serialized = pickle.dumps(value)
            self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f'Cache set error for key {key}: {e}')
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis:
            return False
        try:
            self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f'Cache delete error for key {key}: {e}')
            return False

    def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "market:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.redis:
            return 0
        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f'Cache clear pattern error for {pattern}: {e}')
            return 0

    def is_available(self) -> bool:
        """Check if Redis is available."""
        if not self.redis:
            return False
        try:
            self.redis.ping()
            return True
        except:
            return False

def cached(ttl: int=60, key_prefix: str=''):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        
    Example:
        @cached(ttl=300, key_prefix="market")
        def get_market_data(symbol: str):
            return expensive_api_call(symbol)
    """

    def decorator(func: Callable) -> Callable:

        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f'{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}'
            cached_value = cache_service.get(cache_key)
            if cached_value is not None:
                logger.debug(f'Cache hit for {cache_key}')
                return cached_value
            result = func(*args, **kwargs)
            cache_service.set(cache_key, result, ttl)
            logger.debug(f'Cache miss for {cache_key}, cached with TTL={ttl}s')
            return result
        return wrapper
    return decorator
cache_service = CacheService()