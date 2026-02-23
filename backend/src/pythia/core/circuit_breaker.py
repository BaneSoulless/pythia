"""
Circuit Breaker Pattern for AI-Trading-Bot
SOTA 2026 Resilience Standard

This module implements the Circuit Breaker pattern to prevent cascading failures
in distributed systems. It monitors service health and "trips" the circuit
when failure thresholds are exceeded, allowing time for the failing service to recover.

States:
- CLOSED: Normal operation. Errors are monitored.
- OPEN: Circuit tripped. Calls fail fast.
- HALF-OPEN: Probationary state. Tentative requests allowed.
"""
import time
import functools
import logging
from typing import Callable, Any, Optional
logger = logging.getLogger(__name__)

class CircuitBreakerOpenError(Exception):
    """Raised when the circuit is OPEN and calls are rejected."""
    pass

class CircuitBreaker:
    STATE_CLOSED = 'CLOSED'
    STATE_OPEN = 'OPEN'
    STATE_HALF_OPEN = 'HALF_OPEN'

    def __init__(self, failure_threshold: int=5, recovery_timeout: int=60):
        """
        Initialize Circuit Breaker.

        Args:
            failure_threshold (int): Number of failures before tripping OPEN.
            recovery_timeout (int): Seconds to wait before attempting HALF-OPEN.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = self.STATE_CLOSED
        self.failures = 0
        self.last_failure_time = 0.0

    def __call__(self, func: Callable) -> Callable:
        """Decorator implementation."""

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            self._check_state()
            if self.state == self.STATE_OPEN:
                raise CircuitBreakerOpenError(f'Circuit is OPEN. Retrying in {int(self.recovery_timeout - (time.time() - self.last_failure_time))}s')
            try:
                result = await func(*args, **kwargs)
                if self.state == self.STATE_HALF_OPEN:
                    self._reset()
                return result
            except Exception as e:
                self._record_failure()
                raise e
        return async_wrapper

    def _check_state(self):
        """Evaluates if state should transition from OPEN -> HALF_OPEN."""
        if self.state == self.STATE_OPEN:
            elapsed = time.time() - self.last_failure_time
            if elapsed > self.recovery_timeout:
                logger.info('Circuit Breaker: Entering HALF_OPEN state.')
                self.state = self.STATE_HALF_OPEN

    def _record_failure(self):
        """Records a failure and potentially trips the circuit."""
        self.failures += 1
        self.last_failure_time = time.time()
        if self.state == self.STATE_CLOSED and self.failures >= self.failure_threshold:
            logger.warning(f'Circuit Breaker: Tripped to OPEN (Failures: {self.failures})')
            self.state = self.STATE_OPEN
        elif self.state == self.STATE_HALF_OPEN:
            logger.warning('Circuit Breaker: Re-tripping to OPEN (Failed in HALF_OPEN)')
            self.state = self.STATE_OPEN

    def _reset(self):
        """Resets the breaker to CLOSED state."""
        logger.info('Circuit Breaker: Recovered to CLOSED state.')
        self.state = self.STATE_CLOSED
        self.failures = 0