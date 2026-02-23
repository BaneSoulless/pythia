import pytest
import asyncio
import time
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pythia.infrastructure.persistence.database import Base
from pythia.infrastructure.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from pythia.infrastructure.idempotency.memory_store import IdempotencyLayer
from pythia.infrastructure.persistence.event_store import EventStore, EventLog
SQL_URL = 'sqlite:///:memory:'
engine = create_engine(SQL_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope='module')
def db_session():
    Base.metadata.create_all(bind=engine)
    yield SessionLocal
    Base.metadata.drop_all(bind=engine)

@pytest.mark.asyncio
async def test_circuit_breaker_logic():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

    @cb
    async def failing_service():
        raise ValueError('Service Failed')

    @cb
    async def success_service():
        return 'Success'
    with pytest.raises(ValueError):
        await failing_service()
    with pytest.raises(ValueError):
        await failing_service()
    with pytest.raises(CircuitBreakerOpenError):
        await failing_service()
    await asyncio.sleep(0.15)
    res = await success_service()
    assert res == 'Success'
    assert cb.state == CircuitBreaker.STATE_CLOSED
    print('Circuit Breaker Test: PASSED')

@pytest.mark.asyncio
async def test_idempotency_logic():
    idem = IdempotencyLayer()
    execution_count = 0

    async def sensitive_operation(payload):
        nonlocal execution_count
        execution_count += 1
        return f'Processed {payload}'
    res1 = await idem.process('key-123', sensitive_operation, 'data')
    assert res1 == 'Processed data'
    assert execution_count == 1
    res2 = await idem.process('key-123', sensitive_operation, 'data')
    assert res2 == 'Processed data'
    assert execution_count == 1
    print('Idempotency Test: PASSED')

def test_event_store_persistence(db_session):
    store = EventStore(db_session)
    stream_id = 'trade-xyz'
    ev1 = store.append(stream_id, 'TradeExecuted', {'price': 100, 'qty': 10})
    assert ev1.version == 1
    ev2 = store.append(stream_id, 'TradeSettled', {'fee': 0.5})
    assert ev2.version == 1
    events = store.get_stream(stream_id)
    assert len(events) == 2
    assert events[0].event_type == 'TradeExecuted'
    assert events[1].event_type == 'TradeSettled'
    print('Event Store Test: PASSED')
if __name__ == '__main__':
    asyncio.run(test_circuit_breaker_logic())
    asyncio.run(test_idempotency_logic())
    Base.metadata.create_all(bind=engine)
    test_event_store_persistence(SessionLocal)
    print('ALL CORE TESTS PASSED')
