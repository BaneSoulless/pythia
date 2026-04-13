"""
Circuit Breaker Pattern - Native Implementation

SOTA-2026 resilience pattern preventing cascading failures.
States: CLOSED (normal) -> OPEN (tripped) -> HALF_OPEN (probation) -> CLOSED.

Replaces the fastapi_cb stub with a full native implementation supporting:
- Configurable failure/success thresholds and recovery timeout
- Decorator, context manager, and direct call patterns
- Global registry with metrics reporting
"""

import enum
import logging
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(enum.Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker instance."""

    failure_threshold: int = 5
    success_threshold: int = 2
    recovery_timeout: float = 60.0
    excluded_exceptions: tuple = field(default_factory=tuple)


class CircuitBreakerOpenError(Exception):
    """Raised when the circuit is OPEN and calls are rejected."""

    def __init__(self, service_name: str, retry_after: float):
        self.service_name = service_name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker '{service_name}' is OPEN. "
            f"Retry after {retry_after:.1f}s"
        )


class CircuitBreaker:
    """
    Native circuit breaker with decorator and context manager support.

    Usage:
        breaker = CircuitBreaker("my_api")

        @breaker
        def call_api():
            ...

        with breaker:
            ...
    """

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0

    @property
    def state(self) -> CircuitState:
        """Current state, transitioning OPEN -> HALF_OPEN after timeout."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.config.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info(
                    "circuit_half_open",
                    extra={"breaker": self.name, "elapsed": elapsed},
                )
        return self._state

    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        return self.state == CircuitState.HALF_OPEN

    def _can_execute(self) -> None:
        """Check if execution is allowed. Raises CircuitBreakerOpenError if not."""
        if self.state == CircuitState.OPEN:
            retry_after = (
                self.config.recovery_timeout
                - (time.monotonic() - self._last_failure_time)
            )
            raise CircuitBreakerOpenError(self.name, max(0.0, retry_after))

    def _record_failure(self, error: Exception) -> None:
        """Record a failure and potentially trip the circuit."""
        if isinstance(error, tuple(self.config.excluded_exceptions)):
            return

        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning(
                "circuit_reopened",
                extra={"breaker": self.name, "error": str(error)},
            )
        elif self._failure_count >= self.config.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "circuit_opened",
                extra={
                    "breaker": self.name,
                    "failures": self._failure_count,
                    "error": str(error),
                },
            )

    def _record_success(self) -> None:
        """Record a success and potentially close the circuit."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                logger.info("circuit_closed", extra={"breaker": self.name})
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def reset(self) -> None:
        """Reset to initial CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0

    def get_metrics(self) -> dict[str, Any]:
        """Return current metrics for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
            },
        }

    def __call__(self, func):
        """Decorator pattern."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            self._can_execute()
            try:
                result = func(*args, **kwargs)
                self._record_success()
                return result
            except Exception as e:
                self._record_failure(e)
                raise

        return wrapper

    def __enter__(self):
        """Context manager entry."""
        self._can_execute()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_val is not None:
            self._record_failure(exc_val)
        else:
            self._record_success()
        return False


class CircuitBreakerRegistry:
    """Global registry for circuit breaker instances."""

    _breakers: dict[str, CircuitBreaker] = {}

    @classmethod
    def get_or_create(
        cls, name: str, config: CircuitBreakerConfig | None = None
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        if name not in cls._breakers:
            cls._breakers[name] = CircuitBreaker(name, config)
        return cls._breakers[name]

    @classmethod
    def get_all_metrics(cls) -> list[dict[str, Any]]:
        """Return metrics for all registered breakers."""
        return [b.get_metrics() for b in cls._breakers.values()]

    @classmethod
    def reset_all(cls) -> None:
        """Reset all registered breakers."""
        for breaker in cls._breakers.values():
            breaker.reset()
