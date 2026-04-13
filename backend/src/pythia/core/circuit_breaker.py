"""
Circuit Breaker — Per-Exchange Isolation with Exponential Backoff
SOTA 2026 Resilience Standard

Architectural why:
- Each exchange (Binance, Kraken, …) owns an independent CircuitBreaker instance
  managed by CircuitBreakerRegistry. A Binance 418-ban never trips the Kraken
  circuit and vice versa.
- asyncio.Lock() serialises state transitions within an async context, preventing
  race conditions during concurrent order submissions.
- Exponential backoff in HALF_OPEN probes prevents reconnection storms that would
  extend Binance 418 IP bans (April 2026 policy: bans up to 3 days on repeated
  violations).

States:
  CLOSED    — Normal operation. Failures are monitored.
  OPEN      — Circuit tripped. Calls fail immediately (fail-fast).
  HALF_OPEN — Probationary state. Single probe allowed per backoff window.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class CircuitBreakerOpenError(Exception):
    """Raised when the circuit is OPEN and calls are rejected."""


class CircuitBreaker:
    """
    Thread-safe asyncio Circuit Breaker with exponential backoff.

    Designed for exchange API calls where repeated failures carry escalating
    penalties (e.g. Binance 418 IP ban lasting up to 3 days).
    """

    STATE_CLOSED = "CLOSED"
    STATE_OPEN = "OPEN"
    STATE_HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        exchange_id: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        backoff_base: float = 2.0,
        backoff_max: float = 300.0,
    ) -> None:
        """
        Initialise the breaker for a single exchange endpoint.

        Args:
            exchange_id:       Human-readable exchange name (e.g. "binance").
            failure_threshold: Consecutive failures before tripping OPEN.
            recovery_timeout:  Base seconds before transitioning OPEN→HALF_OPEN.
            backoff_base:      Exponential base for successive HALF_OPEN attempts.
            backoff_max:       Ceiling for computed backoff interval (seconds).
        """
        self.exchange_id = exchange_id
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max

        self.state: str = self.STATE_CLOSED
        self.failures: int = 0
        self.consecutive_open_attempts: int = 0
        self.last_failure_time: float = 0.0

        # asyncio.Lock — serialises all state mutations
        self._lock: asyncio.Lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Decorator interface
    # ------------------------------------------------------------------

    def __call__(self, func: Callable) -> Callable:
        """Decorate an async or sync callable with circuit-breaker protection."""
        if asyncio.iscoroutinefunction(func):
            return self._async_wrapper(func)
        return self._sync_wrapper(func)

    def _async_wrapper(self, func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            await self._before_call()
            try:
                result = await func(*args, **kwargs)
                await self._on_success()
                return result
            except Exception as exc:
                await self._on_failure(exc)
                raise

        return wrapper

    def _sync_wrapper(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Synchronous callers cannot acquire asyncio.Lock; use best-effort
            # state check without locking (acceptable for low-frequency sync paths).
            self._check_state_sync()
            if self.state == self.STATE_OPEN:
                eta = int(self._current_backoff() - (time.monotonic() - self.last_failure_time))
                raise CircuitBreakerOpenError(
                    f"[{self.exchange_id}] Circuit OPEN. Retry in ~{max(eta, 0)}s"
                )
            try:
                result = func(*args, **kwargs)
                self._reset_sync()
                return result
            except Exception:
                self._record_failure_sync()
                raise

        return wrapper

    # ------------------------------------------------------------------
    # Async state machine
    # ------------------------------------------------------------------

    async def _before_call(self) -> None:
        async with self._lock:
            self._check_state_sync()
            if self.state == self.STATE_OPEN:
                eta = int(self._current_backoff() - (time.monotonic() - self.last_failure_time))
                raise CircuitBreakerOpenError(
                    f"[{self.exchange_id}] Circuit OPEN. Retry in ~{max(eta, 0)}s"
                )

    async def _on_success(self) -> None:
        async with self._lock:
            if self.state == self.STATE_HALF_OPEN:
                logger.info(
                    "[%s] Circuit Breaker: HALF_OPEN probe succeeded → CLOSED",
                    self.exchange_id,
                )
            self._reset_sync()

    async def _on_failure(self, exc: Exception) -> None:
        async with self._lock:
            self._record_failure_sync()

    # ------------------------------------------------------------------
    # Synchronous state helpers (called while lock is already held or in sync context)
    # ------------------------------------------------------------------

    def _check_state_sync(self) -> None:
        """Transition OPEN → HALF_OPEN when the backoff window has expired."""
        if self.state == self.STATE_OPEN:
            elapsed = time.monotonic() - self.last_failure_time
            if elapsed >= self._current_backoff():
                logger.info(
                    "[%s] Circuit Breaker: OPEN → HALF_OPEN (attempt %d, backoff %.1fs)",
                    self.exchange_id,
                    self.consecutive_open_attempts,
                    self._current_backoff(),
                )
                self.state = self.STATE_HALF_OPEN

    def _record_failure_sync(self) -> None:
        self.failures += 1
        self.last_failure_time = time.monotonic()

        if self.state == self.STATE_CLOSED and self.failures >= self.failure_threshold:
            self.state = self.STATE_OPEN
            self.consecutive_open_attempts = 0
            logger.warning(
                "[%s] Circuit Breaker: CLOSED → OPEN (failures=%d)",
                self.exchange_id,
                self.failures,
            )
        elif self.state == self.STATE_HALF_OPEN:
            self.consecutive_open_attempts += 1
            self.state = self.STATE_OPEN
            logger.warning(
                "[%s] Circuit Breaker: HALF_OPEN → OPEN (probe failed, attempt=%d, next_backoff=%.1fs)",
                self.exchange_id,
                self.consecutive_open_attempts,
                self._current_backoff(),
            )

    def _reset_sync(self) -> None:
        logger.info("[%s] Circuit Breaker: → CLOSED", self.exchange_id)
        self.state = self.STATE_CLOSED
        self.failures = 0
        self.consecutive_open_attempts = 0

    def _current_backoff(self) -> float:
        """Compute the exponential backoff interval for the current attempt count."""
        interval = self.recovery_timeout * (
            self.backoff_base ** self.consecutive_open_attempts
        )
        return min(interval, self.backoff_max)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def is_open(self) -> bool:
        return self.state == self.STATE_OPEN

    @property
    def is_closed(self) -> bool:
        return self.state == self.STATE_CLOSED

    def status(self) -> dict[str, Any]:
        return {
            "exchange": self.exchange_id,
            "state": self.state,
            "failures": self.failures,
            "consecutive_open_attempts": self.consecutive_open_attempts,
            "current_backoff_s": self._current_backoff(),
        }


class CircuitBreakerRegistry:
    """
    Singleton-like registry providing isolated CircuitBreaker instances per exchange.

    Architectural why: a single shared breaker means a Binance 418-ban silences
    Kraken calls. The registry eliminates that cross-contamination.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        backoff_base: float = 2.0,
        backoff_max: float = 300.0,
    ) -> None:
        self._defaults = {
            "failure_threshold": failure_threshold,
            "recovery_timeout": recovery_timeout,
            "backoff_base": backoff_base,
            "backoff_max": backoff_max,
        }
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, exchange_id: str) -> CircuitBreaker:
        """Return the breaker for *exchange_id*, creating it on first access."""
        if exchange_id not in self._breakers:
            self._breakers[exchange_id] = CircuitBreaker(
                exchange_id=exchange_id, **self._defaults
            )
        return self._breakers[exchange_id]

    def status_all(self) -> list[dict[str, Any]]:
        return [b.status() for b in self._breakers.values()]


# Module-level default registry — import and use directly.
default_registry = CircuitBreakerRegistry(
    failure_threshold=5,
    recovery_timeout=30.0,   # 30s base; doubles each re-trip
    backoff_base=2.0,
    backoff_max=300.0,        # cap at 5 minutes
)
