import pytest
from datetime import datetime
from app.services.backtest_engine import BacktestEngine

@pytest.fixture
def backtest_engine():
    return BacktestEngine(initial_balance=10000.0)

def test_execute_buy(backtest_engine):
    timestamp = datetime.now()
    success = backtest_engine.execute_buy(
        timestamp=timestamp,
        symbol="AAPL",
        quantity=10,
        price=150.0
    )
    
    assert success is True
    assert backtest_engine.balance < 10000.0
    assert backtest_engine.positions["AAPL"] == 10
    assert len(backtest_engine.trades) == 1
    assert backtest_engine.trades[0].side == 'buy'

def test_execute_sell(backtest_engine):
    timestamp = datetime.now()
    # First buy
    backtest_engine.execute_buy(timestamp, "AAPL", 10, 150.0)
    
    # Then sell
    success = backtest_engine.execute_sell(
        timestamp=timestamp,
        symbol="AAPL",
        quantity=5,
        price=160.0
    )
    
    assert success is True
    assert backtest_engine.positions["AAPL"] == 5
    assert len(backtest_engine.trades) == 2
    assert backtest_engine.trades[1].side == 'sell'

def test_calculate_metrics(backtest_engine):
    timestamp = datetime.now()
    # Buy 10 @ 100
    backtest_engine.execute_buy(timestamp, "AAPL", 10, 100.0)
    # Sell 10 @ 110 (Profit)
    backtest_engine.execute_sell(timestamp, "AAPL", 10, 110.0)
    
    # Record equity
    backtest_engine.record_equity(timestamp, {"AAPL": 110.0})
    
    metrics = backtest_engine.calculate_metrics()
    
    assert metrics.total_return > 0
    assert metrics.winning_trades == 1
    assert metrics.losing_trades == 0
    assert metrics.win_rate == 100.0
