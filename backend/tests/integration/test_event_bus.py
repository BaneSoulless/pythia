"""
Test Suite for Distributed Event Bus
Applies Neuro-Symbolic workflow: verifies pub/sub functionality and error isolation.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from pythia.core.event_bus import RedisEventBus, EventBusError
from pythia.domain.events.domain_events import TradeExecutedEvent

@pytest.fixture
def redis_mock():
    with patch("pythia.core.event_bus.redis.from_url") as MockRedis:
        # Construct an async mock that mimics basic pubsub behavior
        mock_instance = AsyncMock()
        mock_pubsub = AsyncMock()
        mock_pubsub.get_message.return_value = None
        mock_instance.pubsub.return_value = mock_pubsub
        MockRedis.return_value = mock_instance
        yield MockRedis

@pytest.mark.asyncio
async def test_event_bus_initialization_assertions():
    """Test Pre-condition: cannot subscribe without event name."""
    bus = RedisEventBus()
    with pytest.raises(AssertionError, match="Event name cannot be empty"):
        @bus.subscribe("")
        def my_bad_handler(data):
            pass

@pytest.mark.asyncio
async def test_event_bus_publish_without_start(redis_mock):
    """Test Edge Case: publishing before start() raises EventBusError."""
    bus = RedisEventBus("redis://dummy")
    with pytest.raises(EventBusError, match="not initialized"):
        await bus.publish(TradeExecutedEvent(symbol="BTC"))

@pytest.mark.asyncio
async def test_event_bus_safe_invoke():
    """Test Neuro-Symbolic logic: handler crash does not crash the bus."""
    bus = RedisEventBus()
    
    # Mocking a crashing handler
    async def crashing_handler(data):
        raise ValueError("Simulated crash")
        
    error_caught = False
    def on_err(data, exc):
        nonlocal error_caught
        error_caught = True
        assert isinstance(exc, ValueError)
        
    bus.on_error(on_err)
    
    # Manually trigger safe_invoke as if message arrived
    await bus._safe_invoke(crashing_handler, "TradeExecutedEvent", {"symbol":"BTC"})
    
    # Ensures the error handler was called and no throw escaped _safe_invoke
    assert error_caught is True
