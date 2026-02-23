"""
Circuit Breaker per chiamate esterne.
Previene failure a cascata su API AI e finanziarie.
"""
import logging
from datetime import timedelta
from functools import wraps
from typing import Callable, Any

try:
    from fastapi_cb import CircuitBreaker, CircuitBreakerError
except ImportError:
    class CircuitBreakerError(Exception): pass
    class CircuitBreaker:
        def __init__(self, fail_max, reset_timeout, excluded_exceptions): pass
        def __call__(self, func):
            @wraps(func)
            async def wrapper(*args, **kwargs): return await func(*args, **kwargs)
            return wrapper

logger = logging.getLogger(__name__)

class BusinessException(Exception):
    """Eccezione di business ignorata dal Circuit Breaker."""
    pass

ai_breaker = CircuitBreaker(
    fail_max=3,
    reset_timeout=timedelta(seconds=60),
    excluded_exceptions=(BusinessException,)
)

financial_api_breaker = CircuitBreaker(
    fail_max=5,
    reset_timeout=timedelta(seconds=120),
    excluded_exceptions=(BusinessException,)
)

@ai_breaker
async def call_groq_api(prompt: str) -> str:
    """Chiama l'API di Groq applicando il Circuit Breaker."""
    logger.info("Chiamata a Groq_API -> %s", prompt[:20])
    return "RESPONSE_MOCK"
