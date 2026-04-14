"""
Tests for StopLossTakeProfitManager service layer.

Covers:
- Stop-loss trigger (mock-based)
- Take-profit trigger (mock-based)
- Trailing stop update
- _close_position success path
- _close_position with symbol=None (validation guard)
- _close_position with DB exception (atomic rollback)
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from pythia.application.stop_loss_manager import StopLossTakeProfitManager
from pythia.core.errors import ErrorCode, TradingError
from pythia.infrastructure.persistence.models import Portfolio, Position


@pytest.fixture
def mock_db_session():
    return MagicMock()


@pytest.fixture
def stop_loss_manager(mock_db_session):
    return StopLossTakeProfitManager(mock_db_session)


# ── Existing regression tests ──────────────────────────────────────────────


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
    position.portfolio_id = 1
    mock_db_session.query.return_value.filter.return_value.all.return_value = [position]
    portfolio = Mock(spec=Portfolio)
    portfolio.id = 1
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
    position.portfolio_id = 1
    mock_db_session.query.return_value.filter.return_value.all.return_value = [position]
    portfolio = Mock(spec=Portfolio)
    portfolio.id = 1
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


# ── P1-A: _close_position edge cases ──────────────────────────────────────


class TestClosePositionValidation:
    """Validate _close_position guards against invalid position data."""

    def test_close_position_symbol_none_raises(self, stop_loss_manager):
        """_close_position must reject positions with symbol=None."""
        position = Mock(spec=Position)
        position.id = 10
        position.symbol = None
        position.quantity = 5.0
        position.current_price = 100.0
        position.portfolio_id = 1

        with pytest.raises(TradingError) as exc_info:
            stop_loss_manager._close_position(position, "stop_loss")

        assert exc_info.value.code == ErrorCode.TRADE_EXECUTION_FAILED
        assert "symbol is None" in exc_info.value.message

    def test_close_position_symbol_empty_raises(self, stop_loss_manager):
        """_close_position must reject positions with empty string symbol."""
        position = Mock(spec=Position)
        position.id = 11
        position.symbol = ""
        position.quantity = 5.0
        position.current_price = 100.0
        position.portfolio_id = 1

        with pytest.raises(TradingError) as exc_info:
            stop_loss_manager._close_position(position, "stop_loss")

        assert exc_info.value.code == ErrorCode.TRADE_EXECUTION_FAILED
        assert "symbol is None" in exc_info.value.message

    def test_close_position_quantity_zero_raises(self, stop_loss_manager):
        """_close_position must reject positions with quantity <= 0."""
        position = Mock(spec=Position)
        position.id = 12
        position.symbol = "AAPL"
        position.quantity = 0
        position.current_price = 100.0
        position.portfolio_id = 1

        with pytest.raises(TradingError) as exc_info:
            stop_loss_manager._close_position(position, "stop_loss")

        assert exc_info.value.code == ErrorCode.TRADE_EXECUTION_FAILED
        assert "invalid quantity" in exc_info.value.message

    def test_close_position_no_current_price_raises(self, stop_loss_manager):
        """_close_position must reject positions with current_price=None."""
        position = Mock(spec=Position)
        position.id = 13
        position.symbol = "AAPL"
        position.quantity = 5.0
        position.current_price = None
        position.portfolio_id = 1

        with pytest.raises(TradingError) as exc_info:
            stop_loss_manager._close_position(position, "stop_loss")

        assert exc_info.value.code == ErrorCode.TRADE_EXECUTION_FAILED
        assert "invalid current_price" in exc_info.value.message

    def test_close_position_no_portfolio_id_raises(self, stop_loss_manager):
        """_close_position must reject positions with portfolio_id=None."""
        position = Mock(spec=Position)
        position.id = 14
        position.symbol = "AAPL"
        position.quantity = 5.0
        position.current_price = 100.0
        position.portfolio_id = None

        with pytest.raises(TradingError) as exc_info:
            stop_loss_manager._close_position(position, "stop_loss")

        assert exc_info.value.code == ErrorCode.TRADE_EXECUTION_FAILED
        assert "portfolio_id is None" in exc_info.value.message


class TestClosePositionSuccess:
    """Validate _close_position success path with mock DB."""

    def test_close_position_ok(self, stop_loss_manager, mock_db_session):
        """Happy path: valid position closes atomically, trade record created."""
        position = Mock(spec=Position)
        position.id = 20
        position.symbol = "TSLA"
        position.quantity = 5.0
        position.current_price = 200.0
        position.average_price = 180.0
        position.portfolio_id = 1

        portfolio = Mock(spec=Portfolio)
        portfolio.id = 1
        portfolio.balance = 5000.0

        # After close, remaining open positions query returns empty
        mock_db_session.execute.return_value.scalar_one.side_effect = [
            position, portfolio
        ]
        mock_db_session.query.return_value.filter.return_value.all.return_value = []

        stop_loss_manager._close_position(position, "stop_loss")

        # Trade record was flushed
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()
        # Position was marked closed
        assert position.status == "closed"
        assert position.exit_reason == "stop_loss"


class TestClosePositionDbException:
    """Validate _close_position handles DB failures with proper wrapping."""

    def test_close_position_db_error_wraps_as_trading_error(
        self, stop_loss_manager, mock_db_session
    ):
        """If the DB raises during atomic_transaction, error must be
        wrapped as TradingError with TRADE_EXECUTION_FAILED and the
        transaction must be rolled back."""
        position = Mock(spec=Position)
        position.id = 30
        position.symbol = "GOOG"
        position.quantity = 2.0
        position.current_price = 150.0
        position.average_price = 140.0
        position.portfolio_id = 1

        # Simulate DB failure on execute (e.g. SELECT FOR UPDATE fails)
        mock_db_session.execute.side_effect = RuntimeError("DB connection lost")

        with pytest.raises(TradingError) as exc_info:
            stop_loss_manager._close_position(position, "stop_loss")

        assert exc_info.value.code == ErrorCode.TRADE_EXECUTION_FAILED
        assert "DB connection lost" in exc_info.value.message
        # Transaction must have been rolled back
        mock_db_session.rollback.assert_called_once()

    def test_close_position_flush_error_rolls_back(
        self, stop_loss_manager, mock_db_session
    ):
        """If flush() raises (e.g. constraint violation), the atomic
        transaction must rollback and error wraps as TradingError."""
        position = Mock(spec=Position)
        position.id = 31
        position.symbol = "AMZN"
        position.quantity = 3.0
        position.current_price = 180.0
        position.average_price = 170.0
        position.portfolio_id = 1

        portfolio = Mock(spec=Portfolio)
        portfolio.id = 1
        portfolio.balance = 10000.0

        mock_db_session.execute.return_value.scalar_one.side_effect = [
            position, portfolio
        ]
        mock_db_session.flush.side_effect = RuntimeError("UNIQUE constraint failed")

        with pytest.raises(TradingError) as exc_info:
            stop_loss_manager._close_position(position, "take_profit")

        assert exc_info.value.code == ErrorCode.TRADE_EXECUTION_FAILED
        assert "UNIQUE constraint failed" in exc_info.value.message
        mock_db_session.rollback.assert_called_once()
