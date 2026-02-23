"""
Comprehensive test suite for P0 security fixes
Run with: pytest tests/test_security_fixes.py -v
"""
import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from pythia.core.validators import PriceValidator, QuantityValidator, SymbolValidator
from pythia.core.errors import ValidationError

class TestPriceValidator:
    """Test strict price validation"""

    def test_valid_prices(self):
        """Valid prices should convert to Decimal"""
        assert PriceValidator.validate(100.5) == Decimal('100.50')
        assert PriceValidator.validate(0.01) == Decimal('0.01')
        assert PriceValidator.validate(999999.99) == Decimal('999999.99')

    def test_negative_price_rejected(self):
        """Negative prices must be rejected"""
        with pytest.raises(ValidationError) as exc:
            PriceValidator.validate(-100)
        assert 'positive' in str(exc.value).lower()

    def test_zero_price_rejected(self):
        """Zero price must be rejected"""
        with pytest.raises(ValidationError):
            PriceValidator.validate(0)

    def test_below_minimum_rejected(self):
        """Prices below minimum must be rejected"""
        with pytest.raises(ValidationError):
            PriceValidator.validate(0.001)

    def test_above_maximum_rejected(self):
        """Prices above maximum must be rejected"""
        with pytest.raises(ValidationError):
            PriceValidator.validate(2000000)

    def test_infinity_rejected(self):
        """Infinity must be rejected"""
        with pytest.raises(ValidationError):
            PriceValidator.validate(float('inf'))

    def test_nan_rejected(self):
        """NaN must be rejected"""
        with pytest.raises(ValidationError):
            PriceValidator.validate(float('nan'))

    def test_precision_rounding(self):
        """Prices should round to 2 decimals"""
        result = PriceValidator.validate(100.999)
        assert result == Decimal('101.00')

class TestQuantityValidator:
    """Test quantity validation"""

    def test_valid_quantities(self):
        """Valid quantities should convert to Decimal"""
        assert QuantityValidator.validate(10.5) == Decimal('10.5000')
        assert QuantityValidator.validate(0.0001) == Decimal('0.0001')

    def test_negative_quantity_rejected(self):
        """Negative quantities must be rejected"""
        with pytest.raises(ValidationError):
            QuantityValidator.validate(-10)

    def test_zero_quantity_rejected(self):
        """Zero quantity must be rejected"""
        with pytest.raises(ValidationError):
            QuantityValidator.validate(0)

class TestSymbolValidator:
    """Test symbol validation"""

    def test_valid_symbols(self):
        """Valid symbols should be uppercase"""
        assert SymbolValidator.validate('aapl') == 'AAPL'
        assert SymbolValidator.validate('MSFT') == 'MSFT'
        assert SymbolValidator.validate('BTC') == 'BTC'

    def test_empty_symbol_rejected(self):
        """Empty symbol must be rejected"""
        with pytest.raises(ValidationError):
            SymbolValidator.validate('')

    def test_special_characters_rejected(self):
        """Symbols with special characters must be rejected"""
        with pytest.raises(ValidationError):
            SymbolValidator.validate('AAPL; DROP TABLE')

    def test_too_long_rejected(self):
        """Symbols exceeding max length must be rejected"""
        with pytest.raises(ValidationError):
            SymbolValidator.validate('A' * 20)

@pytest.mark.asyncio
class TestConcurrentTradeExecution:
    """Test race condition protection"""

    async def test_concurrent_trades_no_race_condition(self, db_session, test_portfolio):
        """100 concurrent trades should not cause race conditions"""
        from pythia.core.enhanced_trading_engine_v2 import EnhancedTradingEngine
        engine = EnhancedTradingEngine(db_session)

        async def execute_trade():
            try:
                return engine.execute_trade(portfolio_id=test_portfolio.id, symbol='AAPL', side='buy', quantity=1, price=150.0)
            except Exception as e:
                return {'error': str(e)}
        tasks = [execute_trade() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        db_session.refresh(test_portfolio)
        assert test_portfolio.balance >= Decimal('10.0')
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if 'error' in r]
        assert len(successful) > 0
        assert len(failed) > 0
        assert test_portfolio.balance >= 0

    async def test_lock_timeout_immediate_failure(self, db_session, test_portfolio):
        """Lock contention should fail immediately with NOWAIT"""
        from pythia.core.enhanced_trading_engine_v2 import atomic_trade_lock
        from pythia.core.errors import TradingError
        with atomic_trade_lock(db_session, test_portfolio.id):
            with pytest.raises(TradingError) as exc:
                with atomic_trade_lock(db_session, test_portfolio.id):
                    pass
            assert 'concurrent' in str(exc.value).lower()

class TestStopLossAtomicity:
    """Test atomic stop-loss execution"""

    def test_position_closure_creates_trade_first(self, db_session, test_position):
        """Trade record must be created before position status update"""
        from pythia.application.stop_loss_manager_v2 import StopLossTakeProfitManager
        manager = StopLossTakeProfitManager(db_session)
        manager._close_position(test_position, 'stop_loss')
        from pythia.infrastructure.persistence.models import Trade
        trade = db_session.query(Trade).filter(Trade.symbol == test_position.symbol, Trade.side == 'sell').first()
        assert trade is not None
        assert trade.pnl is not None
        db_session.refresh(test_position)
        assert test_position.status == 'closed'

    def test_position_closure_rollback_on_error(self, db_session, test_position):
        """Position closure should rollback completely on error"""
        from pythia.application.stop_loss_manager_v2 import StopLossTakeProfitManager
        manager = StopLossTakeProfitManager(db_session)
        with patch.object(db_session, 'commit', side_effect=Exception('Simulated error')):
            with pytest.raises(Exception):
                manager._close_position(test_position, 'stop_loss')
        db_session.refresh(test_position)
        assert test_position.status == 'open'
        from pythia.infrastructure.persistence.models import Trade
        trade_count = db_session.query(Trade).filter(Trade.symbol == test_position.symbol, Trade.side == 'sell').count()
        assert trade_count == 0

@pytest.mark.asyncio
class TestWebSocketAuthentication:
    """Test WebSocket authentication"""

    async def test_websocket_requires_token(self):
        """WebSocket connection without token should be rejected"""
        from pythia.core.websocket_auth import authenticate_websocket
        from fastapi import WebSocket
        mock_ws = Mock(spec=WebSocket)
        mock_ws.query_params = {}
        mock_ws.headers = {}
        mock_ws.close = Mock()
        result = await authenticate_websocket(mock_ws)
        assert result is None
        mock_ws.close.assert_called_once()

    async def test_websocket_invalid_token_rejected(self):
        """WebSocket with invalid token should be rejected"""
        from pythia.core.websocket_auth import authenticate_websocket
        from fastapi import WebSocket
        mock_ws = Mock(spec=WebSocket)
        mock_ws.query_params = {'token': 'invalid_token'}
        mock_ws.headers = {}
        mock_ws.close = Mock()
        result = await authenticate_websocket(mock_ws)
        assert result is None
        mock_ws.close.assert_called_once()

    async def test_websocket_valid_token_accepted(self, valid_jwt_token, test_user):
        """WebSocket with valid token should be accepted"""
        from pythia.core.websocket_auth import authenticate_websocket
        from fastapi import WebSocket
        mock_ws = Mock(spec=WebSocket)
        mock_ws.query_params = {'token': valid_jwt_token}
        mock_ws.headers = {}
        with patch('app.core.websocket_auth.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query().filter().first.return_value = test_user
            mock_get_db.return_value = iter([mock_db])
            result = await authenticate_websocket(mock_ws)
            assert result == test_user

@pytest.fixture
def db_session():
    """Create test database session"""
    from pythia.infrastructure.persistence.database import SessionLocal
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture
def test_portfolio(db_session):
    """Create test portfolio"""
    from pythia.infrastructure.persistence.models import Portfolio, User
    user = User(email='test@test.com', username='testuser', hashed_password='hash')
    db_session.add(user)
    db_session.commit()
    portfolio = Portfolio(user_id=user.id, balance=10000.0, total_value=10000.0)
    db_session.add(portfolio)
    db_session.commit()
    return portfolio

@pytest.fixture
def test_position(db_session, test_portfolio):
    """Create test position"""
    from pythia.infrastructure.persistence.models import Position
    position = Position(portfolio_id=test_portfolio.id, symbol='AAPL', quantity=10.0, average_price=150.0, current_price=155.0, status='open')
    db_session.add(position)
    db_session.commit()
    return position

@pytest.fixture
def test_user(db_session):
    """Create test user"""
    from pythia.infrastructure.persistence.models import User
    user = User(email='test@test.com', username='testuser', hashed_password='hash', is_active=True)
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def valid_jwt_token(test_user):
    """Generate valid JWT token"""
    from jose import jwt
    from pythia.core.config import settings
    from datetime import datetime, timedelta
    payload = {'sub': str(test_user.id), 'exp': datetime.utcnow() + timedelta(minutes=30)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
