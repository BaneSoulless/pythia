"""
Tests for Circuit Breaker Pattern

Validates state transitions, failure counting, and recovery behavior.
"""
import pytest
import time
from unittest.mock import Mock, patch
from pythia.infrastructure.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError, CircuitState, CircuitBreakerRegistry, circuit_breaker

class TestCircuitBreakerStates:
    """Test circuit breaker state transitions."""

    def test_initial_state_is_closed(self):
        """Circuit should start in CLOSED state."""
        breaker = CircuitBreaker('test')
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed

    def test_transitions_to_open_after_failures(self):
        """Circuit should open after failure threshold reached."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker('test', config)
        for _ in range(3):
            breaker._record_failure(Exception('test'))
        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open

    def test_open_circuit_rejects_calls(self):
        """Open circuit should reject calls immediately."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=60)
        breaker = CircuitBreaker('test', config)
        breaker._record_failure(Exception('test'))
        with pytest.raises(CircuitBreakerOpenError) as exc:
            breaker._can_execute()
        assert 'test' in exc.value.service_name
        assert exc.value.retry_after > 0

    def test_transitions_to_half_open_after_timeout(self):
        """Circuit should transition to HALF_OPEN after recovery timeout."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
        breaker = CircuitBreaker('test', config)
        breaker._record_failure(Exception('test'))
        assert breaker.state == CircuitState.OPEN
        time.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN

    def test_half_open_closes_on_success(self):
        """HALF_OPEN should transition to CLOSED on successful calls."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1, success_threshold=2)
        breaker = CircuitBreaker('test', config)
        breaker._record_failure(Exception('test'))
        time.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN
        breaker._record_success()
        breaker._record_success()
        assert breaker.state == CircuitState.CLOSED

    def test_half_open_opens_on_failure(self):
        """HALF_OPEN should transition back to OPEN on failure."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
        breaker = CircuitBreaker('test', config)
        breaker._record_failure(Exception('test'))
        time.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN
        breaker._record_failure(Exception('test'))
        assert breaker.state == CircuitState.OPEN

class TestCircuitBreakerDecorator:
    """Test decorator functionality."""

    def test_decorator_passes_on_success(self):
        """Decorator should pass through successful calls."""
        breaker = CircuitBreaker('test')

        @breaker
        def successful_func():
            return 'success'
        result = successful_func()
        assert result == 'success'

    def test_decorator_records_failure(self):
        """Decorator should record failures."""
        config = CircuitBreakerConfig(failure_threshold=5)
        breaker = CircuitBreaker('test', config)

        @breaker
        def failing_func():
            raise ValueError('test error')
        with pytest.raises(ValueError):
            failing_func()
        assert breaker._failure_count == 1

    def test_decorator_rejects_when_open(self):
        """Decorator should reject calls when circuit is open."""
        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = CircuitBreaker('test', config)

        @breaker
        def test_func():
            return 'success'
        breaker._record_failure(Exception('test'))
        with pytest.raises(CircuitBreakerOpenError):
            test_func()

class TestCircuitBreakerContextManager:
    """Test context manager functionality."""

    def test_context_manager_success(self):
        """Context manager should record success."""
        breaker = CircuitBreaker('test')
        with breaker:
            pass
        assert breaker._failure_count == 0

    def test_context_manager_failure(self):
        """Context manager should record failure on exception."""
        config = CircuitBreakerConfig(failure_threshold=5)
        breaker = CircuitBreaker('test', config)
        with pytest.raises(ValueError):
            with breaker:
                raise ValueError('test')
        assert breaker._failure_count == 1

class TestCircuitBreakerRegistry:
    """Test global registry functionality."""

    def test_get_or_create(self):
        """Registry should create or return existing breaker."""
        CircuitBreakerRegistry._breakers.clear()
        breaker1 = CircuitBreakerRegistry.get_or_create('api_1')
        breaker2 = CircuitBreakerRegistry.get_or_create('api_1')
        assert breaker1 is breaker2

    def test_get_all_metrics(self):
        """Registry should return metrics for all breakers."""
        CircuitBreakerRegistry._breakers.clear()
        CircuitBreakerRegistry.get_or_create('api_1')
        CircuitBreakerRegistry.get_or_create('api_2')
        metrics = CircuitBreakerRegistry.get_all_metrics()
        assert len(metrics) == 2
        names = [m['name'] for m in metrics]
        assert 'api_1' in names
        assert 'api_2' in names

    def test_reset_all(self):
        """Registry should reset all breakers."""
        CircuitBreakerRegistry._breakers.clear()
        breaker = CircuitBreakerRegistry.get_or_create('api_1')
        breaker._record_failure(Exception('test'))
        CircuitBreakerRegistry.reset_all()
        assert breaker._failure_count == 0
        assert breaker.state == CircuitState.CLOSED

class TestCircuitBreakerMetrics:
    """Test metrics reporting."""

    def test_get_metrics(self):
        """Should return complete metrics."""
        config = CircuitBreakerConfig(failure_threshold=5, recovery_timeout=30)
        breaker = CircuitBreaker('test_api', config)
        metrics = breaker.get_metrics()
        assert metrics['name'] == 'test_api'
        assert metrics['state'] == 'closed'
        assert metrics['failure_count'] == 0
        assert metrics['config']['failure_threshold'] == 5
        assert metrics['config']['recovery_timeout'] == 30
