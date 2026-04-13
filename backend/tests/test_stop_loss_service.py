from unittest.mock import MagicMock, Mock

import pytest
from pythia.application.stop_loss_manager import StopLossTakeProfitManager
from pythia.infrastructure.persistence.models import Position


@pytest.fixture
def mock_db_session():
    return MagicMock()


@pytest.fixture
def stop_loss_manager(mock_db_session):
    return StopLossTakeProfitManager(mock_db_session)


def test_check_stop_loss_trigger(stop_loss_manager, mock_db_session):
    position = Mock(spec=Position)
    position.id = 1
    position.status = "open"
    position.symbol = "AAPL"
    position.current_price = 90.0
    position.average_price = 95.0
    position.stop_loss_price = 95.0
    position.take_profit_price = 110.0
    position.trailing_stop_pct = None
    position.quantity = 10.0
    mock_db_session.query.return_value.filter.return_value.all.return_value = [position]
    from pythia.infrastructure.persistence.models import Portfolio
    portfolio = Mock(spec=Portfolio)
    portfolio.balance = 1000.0
    mock_db_session.execute.return_value.scalar_one.side_effect = [position, portfolio]

    triggered = stop_loss_manager.check_all_positions()
    assert len(triggered) == 1
    assert triggered[0]["type"] == "stop_loss"
    assert position.status == "closed"
    assert position.exit_reason == "stop_loss"


def test_check_take_profit_trigger(stop_loss_manager, mock_db_session):
    position = Mock(spec=Position)
    position.id = 2
    position.status = "open"
    position.symbol = "AAPL"
    position.current_price = 115.0
    position.average_price = 100.0
    position.stop_loss_price = 90.0
    position.take_profit_price = 110.0
    position.trailing_stop_pct = None
    position.quantity = 10.0
    mock_db_session.query.return_value.filter.return_value.all.return_value = [position]
    from pythia.infrastructure.persistence.models import Portfolio
    portfolio = Mock(spec=Portfolio)
    portfolio.balance = 1000.0
    mock_db_session.execute.return_value.scalar_one.side_effect = [position, portfolio]

    triggered = stop_loss_manager.check_all_positions()
    assert len(triggered) == 1
    assert triggered[0]["type"] == "take_profit"
    assert position.status == "closed"
    assert position.exit_reason == "take_profit"


def test_update_trailing_stop(stop_loss_manager, mock_db_session):
    position = Mock(spec=Position)
    position.id = 3
    position.status = "open"
    position.symbol = "AAPL"
    position.current_price = 120.0
    position.stop_loss_price = 100.0
    position.take_profit_price = 150.0
    position.trailing_stop_pct = 0.1
    position.quantity = 10.0
    mock_db_session.query.return_value.filter.return_value.all.return_value = [position]
    mock_db_session.execute.return_value.scalar_one.return_value = position
    stop_loss_manager.trailing_stop = True
    stop_loss_manager.check_all_positions()
    assert position.stop_loss_price == 108.0
