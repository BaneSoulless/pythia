"""
Async Event Bus for Decoupled Architecture

Implements publisher/subscriber pattern with asyncio:
- Non-blocking event publishing
- Type-safe event definitions
- Error isolation per handler

SOTA 2026 Implementation - Addresses VOID #1 from adversarial validation.
"""
import asyncio
import logging
from typing import Callable, Dict, List, Any, Optional, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4
logger = logging.getLogger(__name__)
T = TypeVar('T')

class EventType(Enum):
    """Standard event types for trading system."""
    TRADE_EXECUTED = 'trade.executed'
    TRADE_FAILED = 'trade.failed'
    POSITION_OPENED = 'position.opened'
    POSITION_CLOSED = 'position.closed'
    STOP_LOSS_TRIGGERED = 'stop_loss.triggered'
    TAKE_PROFIT_TRIGGERED = 'take_profit.triggered'
    MARKET_DATA_UPDATED = 'market_data.updated'
    PORTFOLIO_UPDATED = 'portfolio.updated'
    CIRCUIT_BREAKER_OPENED = 'circuit_breaker.opened'
    CIRCUIT_BREAKER_CLOSED = 'circuit_breaker.closed'
    SYSTEM_ERROR = 'system.error'
    SYSTEM_WARNING = 'system.warning'

@dataclass
class Event:
    """Base event class."""
    type: EventType
    data: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = 'unknown'
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {'event_id': self.event_id, 'type': self.type.value, 'data': self.data, 'timestamp': self.timestamp.isoformat(), 'source': self.source, 'correlation_id': self.correlation_id}
EventHandler = Callable[[Event], Any]

class AsyncEventBus:
    """
    Async event bus for non-blocking event processing.
    
    Usage:
        bus = AsyncEventBus()
        
        @bus.subscribe(EventType.TRADE_EXECUTED)
        async def on_trade(event: Event):
            print(f"Trade executed: {event.data}")
        
        await bus.publish(Event(
            type=EventType.TRADE_EXECUTED,
            data={"symbol": "AAPL", "quantity": 10}
        ))
    """

    def __init__(self, max_queue_size: int=1000):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running: bool = False
        self._worker_task: Optional[asyncio.Task] = None
        self._error_handlers: List[Callable[[Event, Exception], Any]] = []

    def subscribe(self, event_type: EventType) -> Callable[[EventHandler], EventHandler]:
        """
        Decorator for subscribing to events.
        
        Usage:
            @bus.subscribe(EventType.TRADE_EXECUTED)
            async def handle_trade(event: Event):
                ...
        """

        def decorator(handler: EventHandler) -> EventHandler:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            logger.debug(f'Handler registered for {event_type.value}')
            return handler
        return decorator

    def add_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """Programmatically add event handler."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def remove_handler(self, event_type: EventType, handler: EventHandler) -> bool:
        """Remove event handler. Returns True if removed."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                return True
            except ValueError:
                pass
        return False

    def on_error(self, handler: Callable[[Event, Exception], Any]) -> None:
        """Register error handler for failed event processing."""
        self._error_handlers.append(handler)

    async def publish(self, event: Event) -> None:
        """
        Publish event to bus (non-blocking).
        
        Events are queued and processed asynchronously.
        """
        try:
            self._queue.put_nowait(event)
            logger.debug(f'Event published: {event.type.value}')
        except asyncio.QueueFull:
            logger.error(f'Event queue full, dropping event: {event.event_id}')

    async def publish_sync(self, event: Event) -> List[Any]:
        """
        Publish and wait for all handlers to complete.
        
        Returns list of handler results.
        """
        return await self._dispatch(event)

    async def _dispatch(self, event: Event) -> List[Any]:
        """Dispatch event to all registered handlers."""
        handlers = self._handlers.get(event.type, [])
        if not handlers:
            return []
        results = []
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(event)
                else:
                    result = handler(event)
                results.append(result)
            except Exception as e:
                logger.error(f'Handler error for {event.type.value}: {e}', exc_info=True)
                for error_handler in self._error_handlers:
                    try:
                        if asyncio.iscoroutinefunction(error_handler):
                            await error_handler(event, e)
                        else:
                            error_handler(event, e)
                    except Exception:
                        pass
        return results

    async def _worker(self) -> None:
        """Background worker for processing queued events."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._dispatch(event)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f'Event worker error: {e}', exc_info=True)

    async def start(self) -> None:
        """Start event bus worker."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info('Event bus started')

    async def stop(self, timeout: float=5.0) -> None:
        """Stop event bus and drain queue."""
        self._running = False
        if self._worker_task:
            try:
                await asyncio.wait_for(self._worker_task, timeout=timeout)
            except asyncio.TimeoutError:
                self._worker_task.cancel()
        logger.info('Event bus stopped')

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {'running': self._running, 'queue_size': self._queue.qsize(), 'handler_counts': {et.value: len(handlers) for et, handlers in self._handlers.items()}}
_event_bus: Optional[AsyncEventBus] = None

def get_event_bus() -> AsyncEventBus:
    """Get global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = AsyncEventBus()
    return _event_bus

async def emit(event_type: EventType, data: Dict[str, Any], source: str='system', correlation_id: Optional[str]=None) -> None:
    """
    Convenience function for emitting events.
    
    Usage:
        await emit(EventType.TRADE_EXECUTED, {
            "symbol": "AAPL",
            "quantity": 10,
            "price": 150.0
        })
    """
    event = Event(type=event_type, data=data, source=source, correlation_id=correlation_id)
    await get_event_bus().publish(event)

def trade_executed_event(portfolio_id: int, symbol: str, side: str, quantity: float, price: float, pnl: Optional[float]=None) -> Event:
    """Create trade executed event."""
    return Event(type=EventType.TRADE_EXECUTED, data={'portfolio_id': portfolio_id, 'symbol': symbol, 'side': side, 'quantity': quantity, 'price': price, 'pnl': pnl}, source='trading_engine')

def stop_loss_triggered_event(portfolio_id: int, symbol: str, trigger_price: float, quantity: float) -> Event:
    """Create stop loss triggered event."""
    return Event(type=EventType.STOP_LOSS_TRIGGERED, data={'portfolio_id': portfolio_id, 'symbol': symbol, 'trigger_price': trigger_price, 'quantity': quantity}, source='stop_loss_manager')