import pytest
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from app.services.backtest_engine import BacktestEngine
from app.services.websocket_manager import ConnectionManager
from app.services.stop_loss_manager import StopLossTakeProfitManager
from app.services.market_data import MarketDataService
from app.db.models import Position

# --- Test 1: Complex Backtest Strategy ---
def test_backtest_complex_strategy():
    """
    Analista Scenario: Verify state consistency across a complex sequence of trades.
    Sequence: Buy -> Partial Sell -> Buy More -> Sell All.
    """
    engine = BacktestEngine(initial_balance=10000.0)
    ts = datetime.now()
    
    # 1. Buy 10 @ 100
    assert engine.execute_buy(ts, "AAPL", 10, 100.0)
    assert engine.positions["AAPL"] == 10
    assert engine.balance < 10000.0
    
    # 2. Partial Sell 5 @ 110
    assert engine.execute_sell(ts, "AAPL", 5, 110.0)
    assert engine.positions["AAPL"] == 5
    
    # 3. Buy More 5 @ 120
    assert engine.execute_buy(ts, "AAPL", 5, 120.0)
    assert engine.positions["AAPL"] == 10
    
    # 4. Sell All 10 @ 130
    assert engine.execute_sell(ts, "AAPL", 10, 130.0)
    assert "AAPL" not in engine.positions
    
    # Verify final metrics
    metrics = engine.calculate_metrics()
    assert metrics.num_trades == 4
    assert metrics.final_balance > 10000.0  # Should be profitable

# --- Test 2: WebSocket Concurrency ---
@pytest.mark.asyncio
async def test_websocket_concurrency():
    """
    Programmatore Capo Scenario: Stress test connection manager with concurrent operations.
    """
    manager = ConnectionManager()
    
    # Simulate 50 concurrent connections
    num_clients = 50
    mock_sockets = [AsyncMock() for _ in range(num_clients)]
    
    async def connect_client(ws):
        await manager.connect(ws)
        
    # Run concurrent connects
    await asyncio.gather(*[connect_client(ws) for ws in mock_sockets])
    
    assert len(manager.active_connections) == num_clients
    
    # Broadcast to all
    await manager.broadcast({"type": "stress_test"})
    
    for ws in mock_sockets:
        ws.send_json.assert_called()
        
    # Concurrent disconnects
    for ws in mock_sockets:
        manager.disconnect(ws)
        
    assert len(manager.active_connections) == 0

# --- Test 3: Stop Loss Slippage (Gap Down) ---
def test_stop_loss_slippage():
    """
    Analista Scenario: Market opens significantly below stop price (Gap Down).
    The system should execute at the OPEN price (slippage), not the STOP price.
    """
    mock_db = MagicMock()
    manager = StopLossTakeProfitManager(mock_db)
    
    # Position: Bought at 100, Stop at 95
    position = Mock(spec=Position)
    position.status = "open"
    position.symbol = "AAPL"
    position.average_price = 100.0
    position.stop_loss_price = 95.0
    position.take_profit_price = 110.0
    
    # Market crashes to 80 (Gap Down)
    position.current_price = 80.0 
    
    mock_db.query.return_value.filter.return_value.all.return_value = [position]
    
    triggered = manager.check_all_positions()
    
    assert len(triggered) == 1
    assert triggered[0]["type"] == "stop_loss"
    # Critical: Execution price should be the current market price (80), NOT the stop price (95)
    assert triggered[0]["price"] == 80.0
    assert position.exit_price == 80.0

# --- Test 4: Market Data Corruption ---
def test_market_data_corruption():
    """
    Programmatore Capo Scenario: Handle malformed/garbage data from provider.
    """
    service = MarketDataService()
    
    with patch('yfinance.Ticker') as mock_ticker:
        # Simulate complete garbage/exception from library
        mock_ticker.side_effect = Exception("API Connection Failed")
        
        # Should not crash, but return error structure
        result = service.get_quote("INVALID")
        
        assert "error" in result
        assert result["price"] == 0.0
        assert result["symbol"] == "INVALID"
