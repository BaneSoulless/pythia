import pytest
from unittest.mock import Mock, MagicMock
from app.services.stop_loss_manager import StopLossTakeProfitManager
from app.db.models import Position

@pytest.fixture
def mock_db_session():
    return MagicMock()

@pytest.fixture
def stop_loss_manager(mock_db_session):
    return StopLossTakeProfitManager(mock_db_session)

def test_check_stop_loss_trigger(stop_loss_manager, mock_db_session):
    # Setup open position with SL triggered
    position = Mock(spec=Position)
    position.status = "open"
    position.symbol = "AAPL"
    position.current_price = 90.0
    position.stop_loss_price = 95.0
    position.take_profit_price = 110.0
    position.trailing_stop_pct = None
    
    mock_db_session.query.return_value.filter.return_value.all.return_value = [position]
    
    triggered = stop_loss_manager.check_all_positions()
    
    assert len(triggered) == 1
    assert triggered[0]["type"] == "stop_loss"
    assert position.status == "closed"
    assert position.exit_reason == "stop_loss"

def test_check_take_profit_trigger(stop_loss_manager, mock_db_session):
    # Setup open position with TP triggered
    position = Mock(spec=Position)
    position.status = "open"
    position.symbol = "AAPL"
    position.current_price = 115.0
    position.stop_loss_price = 90.0
    position.take_profit_price = 110.0
    position.trailing_stop_pct = None
    
    mock_db_session.query.return_value.filter.return_value.all.return_value = [position]
    
    triggered = stop_loss_manager.check_all_positions()
    
    assert len(triggered) == 1
    assert triggered[0]["type"] == "take_profit"
    assert position.status == "closed"
    assert position.exit_reason == "take_profit"

def test_update_trailing_stop(stop_loss_manager, mock_db_session):
    # Setup open position with trailing stop
    position = Mock(spec=Position)
    position.status = "open"
    position.symbol = "AAPL"
    position.current_price = 120.0
    position.stop_loss_price = 100.0
    position.take_profit_price = 150.0
    position.trailing_stop_pct = 0.1  # 10% trailing
    
    mock_db_session.query.return_value.filter.return_value.all.return_value = [position]
    
    stop_loss_manager.trailing_stop = True
    stop_loss_manager.check_all_positions()
    
    # New stop loss should be 120 * (1 - 0.1) = 108.0
    # Since 108.0 > 100.0, it should update
    assert position.stop_loss_price == 108.0
