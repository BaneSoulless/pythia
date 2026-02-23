import pytest
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from pythia.application.backtest_engine import BacktestEngine
from pythia.application.websocket_manager import ConnectionManager
from pythia.application.stop_loss_manager import StopLossTakeProfitManager
from pythia.application.market_data import MarketDataService
from pythia.infrastructure.persistence.models import Position

def test_backtest_complex_strategy():
    """
    Analista Scenario: Verify state consistency across a complex sequence of trades.
    Sequence: Buy -> Partial Sell -> Buy More -> Sell All.
    """
    engine = BacktestEngine(initial_balance=10000.0)
    ts = datetime.now()
    assert engine.execute_buy(ts, 'AAPL', 10, 100.0)
    assert engine.positions['AAPL'] == 10
    assert engine.balance < 10000.0
    assert engine.execute_sell(ts, 'AAPL', 5, 110.0)
    assert engine.positions['AAPL'] == 5
    assert engine.execute_buy(ts, 'AAPL', 5, 120.0)
    assert engine.positions['AAPL'] == 10
    assert engine.execute_sell(ts, 'AAPL', 10, 130.0)
    assert 'AAPL' not in engine.positions
    metrics = engine.calculate_metrics()
    assert metrics.num_trades == 4
    assert metrics.final_balance > 10000.0

@pytest.mark.asyncio
async def test_websocket_concurrency():
    """
    Programmatore Capo Scenario: Stress test connection manager with concurrent operations.
    """
    manager = ConnectionManager()
    num_clients = 50
    mock_sockets = [AsyncMock() for _ in range(num_clients)]

    async def connect_client(ws):
        await manager.connect(ws)
    await asyncio.gather(*[connect_client(ws) for ws in mock_sockets])
    assert len(manager.active_connections) == num_clients
    await manager.broadcast({'type': 'stress_test'})
    for ws in mock_sockets:
        ws.send_json.assert_called()
    for ws in mock_sockets:
        manager.disconnect(ws)
    assert len(manager.active_connections) == 0

def test_stop_loss_slippage():
    """
    Analista Scenario: Market opens significantly below stop price (Gap Down).
    The system should execute at the OPEN price (slippage), not the STOP price.
    """
    mock_db = MagicMock()
    manager = StopLossTakeProfitManager(mock_db)
    position = Mock(spec=Position)
    position.status = 'open'
    position.symbol = 'AAPL'
    position.average_price = 100.0
    position.stop_loss_price = 95.0
    position.take_profit_price = 110.0
    position.current_price = 80.0
    mock_db.query.return_value.filter.return_value.all.return_value = [position]
    triggered = manager.check_all_positions()
    assert len(triggered) == 1
    assert triggered[0]['type'] == 'stop_loss'
    assert triggered[0]['price'] == 80.0
    assert position.exit_price == 80.0

def test_market_data_corruption():
    """
    Programmatore Capo Scenario: Handle malformed/garbage data from provider.
    """
    service = MarketDataService()
    with patch('yfinance.Ticker') as mock_ticker:
        mock_ticker.side_effect = Exception('API Connection Failed')
        result = service.get_quote('INVALID')
        assert 'error' in result
        assert result['price'] == 0.0
        assert result['symbol'] == 'INVALID'
