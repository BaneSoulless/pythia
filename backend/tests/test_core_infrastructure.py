import asyncio
import os
import sys

import pytest

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
from pythia.infrastructure.event_store import EventStore  # noqa: E402
from pythia.infrastructure.idempotency.memory_store import IdempotencyLayer  # noqa: E402
from pythia.infrastructure.persistence.models import Base  # noqa: E402
from pythia.infrastructure.resilience.circuit_breaker import (  # noqa: E402
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
)
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

SQL_URL = "sqlite:///:memory:"
engine = create_engine(SQL_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    yield SessionLocal
    Base.metadata.drop_all(bind=engine)


@pytest.mark.asyncio
async def test_circuit_breaker_logic():
    config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.1)
    cb = CircuitBreaker("test_service", config)

    @cb
    def failing_service():
        raise ValueError("Service Failed")

    @cb
    def success_service():
        return "Success"

    with pytest.raises(ValueError):
        failing_service()
    with pytest.raises(ValueError):
        failing_service()
    with pytest.raises(CircuitBreakerOpenError):
        failing_service()
    await asyncio.sleep(0.15)
    res = success_service()
    assert res == "Success"
    assert cb.state in [CircuitState.CLOSED, CircuitState.HALF_OPEN]


@pytest.mark.asyncio
async def test_idempotency_logic():
    idem = IdempotencyLayer()
    execution_count = 0

    async def sensitive_operation(payload):
        nonlocal execution_count
        execution_count += 1
        return f"Processed {payload}"

    res1 = await idem.process("key-123", sensitive_operation, "data")
    assert res1 == "Processed data"
    assert execution_count == 1
    res2 = await idem.process("key-123", sensitive_operation, "data")
    assert res2 == "Processed data"
    assert execution_count == 1


def test_event_store_persistence(db_session):
    store = EventStore(db_session)
    stream_id = "trade-xyz"
    ev1 = store.append(stream_id, "TradeExecuted", {"price": 100, "qty": 10})
    assert ev1.version == 1
    ev2 = store.append(stream_id, "TradeSettled", {"fee": 0.5})
    assert ev2.version == 1
    events = store.get_stream(stream_id)
    assert len(events) == 2
    assert events[0].event_type == "TradeExecuted"
    assert events[1].event_type == "TradeSettled"


if __name__ == "__main__":
    asyncio.run(test_circuit_breaker_logic())
    asyncio.run(test_idempotency_logic())
    Base.metadata.create_all(bind=engine)
    test_event_store_persistence(SessionLocal)
    print("ALL CORE TESTS PASSED")
