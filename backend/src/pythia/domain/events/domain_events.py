"""Domain Events for Pythia v4.0 Event-Driven Architecture.

Immutable events emitted by domain logic. Consumed by infrastructure
(Prometheus, EventBus, Celery) for side effects and persistence.
"""
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass(frozen=True)
class DomainEvent:
    """Base domain event. All events must be immutable."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: str = ""


@dataclass(frozen=True)
class ArbitrageDetectedEvent(DomainEvent):
    """Emitted when cross-platform arbitrage opportunity is found."""
    platform_a: str = ""
    platform_b: str = ""
    market_description: str = ""
    roi: float = 0.0
    cost: float = 0.0
    profit: float = 0.0
    strategy: str = ""


@dataclass(frozen=True)
class TradeExecutedEvent(DomainEvent):
    """Emitted after successful trade execution on any platform."""
    symbol: str = ""
    side: str = ""
    quantity: float = 0.0
    price: float = 0.0
    pnl: float = 0.0
    platform: str = ""
    asset_class: str = ""


@dataclass(frozen=True)
class CircuitBreakerTrippedEvent(DomainEvent):
    """Emitted when a circuit breaker transitions to OPEN."""
    platform: str = ""
    failure_count: int = 0
    recovery_timeout_s: int = 60


@dataclass(frozen=True)
class SignalGeneratedEvent(DomainEvent):
    """Emitted when AI generates a new trading signal."""
    pair: str = ""
    action: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    provider: str = ""
