import asyncio
import functools
from typing import Callable

def simple_circuit_breaker(max_retries: int=3, backoff_base: float=2.0):
    """Exponential backoff retry decorator for test mode."""

    def decorator(func: Callable):

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    wait = backoff_base ** attempt
                    await asyncio.sleep(wait)
            raise RuntimeError(f'Max retries ({max_retries}) exceeded')
        return wrapper
    return decorator