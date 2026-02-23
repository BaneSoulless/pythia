"""
Tests for stop-loss and take-profit automation.

Tests trigger conditions, position management, and automated order execution.
"""
import pytest
from decimal import Decimal
from app.services.stop_loss_manager import StopLossTakeProfitManager as StopLossManager
from app.core.errors import TradingError
from app.db.models import Portfolio, Position, User


class TestStopLossTakeProfit:
    """Test suite for stop-loss and take-profit functionality."""
    
    @pytest.fixture
    def manager(self, db_session):
        """Create stop-loss manager instance."""
        return StopLossManager(db_session)
    
    @pytest.fixture
    def portfolio_with_position(self, db_session):
        """Create portfolio with a position."""
        user = User(email="test@example.com", username="testuser", hashed_password="hash")
        db_session.add(user)
        db_session.commit()
        
        portfolio = Portfolio(user_id=user.id, balance=10000.0, total_value=11500.0)
        db_session.add(portfolio)
        db_session.flush()

        position = Position(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            quantity=10,
            average_price=150.0,
            current_price=150.0,
            stop_loss_price=147.0,  # 2% stop loss
            take_profit_price=157.5   # 5% take profit
        )
        db_session.add(position)
        db_session.commit()

        return portfolio, position

    def test_stop_loss_trigger(self, manager, portfolio_with_position, db_session):
        """Test stop-loss triggers when price drops."""
        portfolio, position = portfolio_with_position

        # Update price to below stop-loss
        position.current_price = 146.0
        db_session.commit()

        # Check stop-loss triggers
        manager.check_all_positions()

        # Position should be closed
        db_session.refresh(position)
        assert position.quantity == 0 or position.status == "closed"

    def test_take_profit_trigger(self, manager, portfolio_with_position, db_session):
        """Test take-profit triggers when price rises."""
        portfolio, position = portfolio_with_position

        # Update price to above take-profit
        position.current_price = 158.0
        db_session.commit()

        # Check take-profit triggers
        manager.check_all_positions()

        # Position should be closed
        db_session.refresh(position)
        assert position.quantity == 0 or position.status == "closed"

    def test_trailing_stop_loss(self, manager, portfolio_with_position, db_session):
        """Test trailing stop-loss adjusts with price."""
        portfolio, position = portfolio_with_position
        position.trailing_stop_pct = 0.02  # 2% trailing
        db_session.commit()

        # Price rises
        position.current_price = 155.0
        manager.update_trailing_stops()

        db_session.refresh(position)
        # Stop loss should have moved up
        assert position.stop_loss_price > 147.0

    def test_no_trigger_within_range(self, manager, portfolio_with_position, db_session):
        """Test no trigger when price within range."""
        portfolio, position = portfolio_with_position

        # Price within range
        position.current_price = 152.0
        db_session.commit()

        original_quantity = position.quantity
        manager.check_all_positions()

        db_session.refresh(position)
        assert position.quantity == original_quantity

    def test_set_stop_loss_take_profit(self, manager, portfolio_with_position, db_session):
        """Test setting SL/TP on position."""
        portfolio, position = portfolio_with_position

        manager.set_stop_loss_take_profit(
            position_id=position.id,
            stop_loss_pct=0.03,  # 3%
            take_profit_pct=0.10  # 10%
        )

        db_session.refresh(position)
        assert position.stop_loss_price == pytest.approx(145.5, rel=0.01)
        assert position.take_profit_price == pytest.approx(165.0, rel=0.01)

    def test_risk_reward_calculation(self, manager, portfolio_with_position):
        """Test risk/reward ratio calculation."""
        portfolio, position = portfolio_with_position

        risk_reward = manager.calculate_risk_reward(
            entry_price=150.0,
            stop_loss_price=147.0,
            take_profit_price=157.5
        )

        # Risk: 3, Reward: 7.5, Ratio: 2.5
        assert risk_reward == pytest.approx(2.5, rel= 0.01)
