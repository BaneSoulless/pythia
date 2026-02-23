"""
SECURITY FIXES - Critical Vulnerability Patches
Apply these fixes in priority order (P0 first)
"""

# ============================================================================
# P0 FIX #1: Race Condition Protection in Trading Engine
# ============================================================================

from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy import select
from decimal import Decimal

@contextmanager
def atomic_trade_lock(db: Session, portfolio_id: int):
    """Acquire exclusive lock on portfolio for trade execution"""
    try:
        # Lock portfolio row with NOWAIT to fail fast on contention
        portfolio = db.execute(
            select(Portfolio)
            .where(Portfolio.id == portfolio_id)
            .with_for_update(nowait=True)
        ).scalar_one()
        
        yield portfolio
        db.commit()
    except Exception as e:
        db.rollback()
        raise TradingError(
            code=ErrorCode.DB_TRANSACTION_FAILED,
            message="Trade lock acquisition failed - concurrent modification detected"
        )


# ============================================================================
# P0 FIX #2: Atomic Stop-Loss Execution
# ============================================================================

class StopLossTakeProfitManager:
    def _close_position(self, position: Position, reason: str):
        """Close position with full atomicity"""
        try:
            with atomic_transaction(self.db):
                # Lock position
                locked_pos = self.db.execute(
                    select(Position)
                    .where(Position.id == position.id)
                    .with_for_update()
                ).scalar_one()
                
                # Create trade record FIRST
                trade = Trade(
                    portfolio_id=locked_pos.portfolio_id,
                    symbol=locked_pos.symbol,
                    side='sell',
                    quantity=locked_pos.quantity,
                    price=locked_pos.current_price,
                    pnl=(locked_pos.current_price - locked_pos.average_price) * locked_pos.quantity
                )
                self.db.add(trade)
                
                # Update position status
                locked_pos.status = "closed"
                locked_pos.exit_price = locked_pos.current_price
                locked_pos.exit_date = datetime.utcnow()
                locked_pos.exit_reason = reason
                
                # Update portfolio balance
                portfolio = self.db.query(Portfolio).with_for_update().filter(
                    Portfolio.id == locked_pos.portfolio_id
                ).first()
                portfolio.balance += locked_pos.quantity * locked_pos.current_price
                
                # Commit happens in context manager
        except Exception as e:
            logger.error(f"Stop-loss execution failed: {e}", exc_info=True)
            raise


# ============================================================================
# P0 FIX #3: Strict Price Validation
# ============================================================================

from decimal import Decimal, InvalidOperation

class PriceValidator:
    MIN_PRICE = Decimal("0.01")
    MAX_PRICE = Decimal("1000000.00")
    MAX_DECIMALS = 2
    
    @staticmethod
    def validate_price(price: float) -> Decimal:
        """Validate and normalize price to Decimal"""
        try:
            price_decimal = Decimal(str(price))
        except (InvalidOperation, ValueError):
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid price format: {price}"
            )
        
        if price_decimal <= 0:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Price must be positive, got: {price}"
            )
        
        if price_decimal < PriceValidator.MIN_PRICE:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Price below minimum: {price} < {PriceValidator.MIN_PRICE}"
            )
        
        if price_decimal > PriceValidator.MAX_PRICE:
            raise ValidationError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Price exceeds maximum: {price} > {PriceValidator.MAX_PRICE}"
            )
        
        return price_decimal.quantize(Decimal('0.01'))


# Enhanced validate_trade method
def validate_trade(self, portfolio_id: int, symbol: str, side: str, 
                   quantity: float, price: float) -> tuple[bool, str]:
    """Enhanced validation with strict type checking"""
    
    # Validate price using Decimal
    try:
        price_decimal = PriceValidator.validate_price(price)
    except ValidationError as e:
        return False, e.message
    
    # Validate quantity
    if quantity <= 0 or quantity > 1e6:
        return False, f"Invalid quantity: {quantity}"
    
    # Validate symbol format
    if not symbol or not symbol.isalnum() or len(symbol) > 10:
        return False, f"Invalid symbol format: {symbol}"
    
    # Rest of validation...
    return True, "OK"


# ============================================================================
# P0 FIX #4: WebSocket Authentication
# ============================================================================

from fastapi import WebSocket, WebSocketDisconnect, status
from jose import jwt, JWTError

async def authenticate_websocket(websocket: WebSocket) -> Optional[User]:
    """Authenticate WebSocket connection via JWT token"""
    try:
        # Extract token from query params or headers
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
        
        # Verify JWT
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
        
        # Fetch user from database
        db = next(get_db())
        user = db.query(User).filter(User.id == int(user_id)).first()
        
        if not user or not user.is_active:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
        
        return user
        
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None


@app.websocket("/ws/portfolio/{portfolio_id}")
async def websocket_portfolio(websocket: WebSocket, portfolio_id: int):
    """Authenticated WebSocket endpoint"""
    await websocket.accept()
    
    # Authenticate
    user = await authenticate_websocket(websocket)
    if not user:
        return
    
    # Verify portfolio ownership
    db = next(get_db())
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user.id
    ).first()
    
    if not portfolio:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Continue with authenticated connection
    await portfolio_websocket_endpoint(websocket, portfolio_id)


# ============================================================================
# P1 FIX #5: Decimal-Based Financial Calculations
# ============================================================================

from decimal import Decimal, ROUND_HALF_UP

class FinancialCalculator:
    """All financial calculations using Decimal for precision"""
    
    @staticmethod
    def calculate_trade_cost(quantity: Decimal, price: Decimal, 
                            commission_rate: Decimal = Decimal("0.001")) -> Decimal:
        """Calculate total trade cost with commission"""
        base_cost = quantity * price
        commission = (base_cost * commission_rate).quantize(Decimal('0.01'), ROUND_HALF_UP)
        return base_cost + commission
    
    @staticmethod
    def calculate_pnl(entry_price: Decimal, exit_price: Decimal, 
                     quantity: Decimal) -> Decimal:
        """Calculate profit/loss"""
        return ((exit_price - entry_price) * quantity).quantize(Decimal('0.01'))
    
    @staticmethod
    def check_sufficient_balance(balance: Decimal, cost: Decimal, 
                                 min_balance: Decimal) -> bool:
        """Check if trade leaves sufficient balance"""
        remaining = balance - cost
        return remaining >= min_balance


# Update database models to use Decimal
from sqlalchemy import Numeric

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    balance = Column(Numeric(precision=15, scale=2), default=Decimal("10000.00"))
    total_value = Column(Numeric(precision=15, scale=2), default=Decimal("10000.00"))


# ============================================================================
# P1 FIX #6: Position Limit Enforcement
# ============================================================================

class EnhancedTradingEngine:
    MAX_POSITIONS_PER_PORTFOLIO = 50
    
    def validate_trade(self, portfolio_id: int, symbol: str, side: str,
                      quantity: float, price: float) -> tuple[bool, str]:
        """Enhanced validation with position limits"""
        
        # Check position count for buy orders
        if side == 'buy':
            position_count = self.db.query(Position).filter(
                Position.portfolio_id == portfolio_id,
                Position.status == 'open'
            ).count()
            
            # Check if adding new position
            existing_position = self.db.query(Position).filter(
                Position.portfolio_id == portfolio_id,
                Position.symbol == symbol,
                Position.status == 'open'
            ).first()
            
            if not existing_position and position_count >= self.MAX_POSITIONS_PER_PORTFOLIO:
                return False, f"Maximum positions limit reached: {self.MAX_POSITIONS_PER_PORTFOLIO}"
        
        # Rest of validation...
        return True, "OK"


# ============================================================================
# P1 FIX #7: Trailing Stop for Short Positions
# ============================================================================

class StopLossTakeProfitManager:
    def _update_trailing_stop(self, position: Position):
        """Update trailing stop with support for short positions"""
        if not position.trailing_stop_pct:
            return
        
        # Determine position direction
        is_long = position.quantity > 0
        
        if is_long:
            # Long position: stop loss moves UP as price increases
            new_stop_loss = position.current_price * (1 - position.trailing_stop_pct)
            if not position.stop_loss_price or new_stop_loss > position.stop_loss_price:
                position.stop_loss_price = new_stop_loss
        else:
            # Short position: stop loss moves DOWN as price decreases
            new_stop_loss = position.current_price * (1 + position.trailing_stop_pct)
            if not position.stop_loss_price or new_stop_loss < position.stop_loss_price:
                position.stop_loss_price = new_stop_loss
        
        self.db.commit()


# ============================================================================
# P1 FIX #8: Backtest Look-Ahead Bias Prevention
# ============================================================================

class BacktestEngine:
    def run_backtest(self, strategy_func, historical_data: pd.DataFrame):
        """Run backtest with strict temporal isolation"""
        for i in range(len(historical_data)):
            # Only pass data UP TO current timestamp
            visible_data = historical_data.iloc[:i+1].copy()
            current_row = historical_data.iloc[i]
            
            # Strategy can only see past data
            decision = strategy_func(visible_data)
            
            # Execute trade at NEXT bar's open (realistic slippage)
            if i < len(historical_data) - 1:
                execution_price = historical_data.iloc[i+1]['open']
            else:
                execution_price = current_row['close']
            
            if decision == 'buy':
                self.execute_buy(current_row['timestamp'], symbol, quantity, execution_price)


# ============================================================================
# P2 FIX #9: Secure Error Handling
# ============================================================================

class SecureErrorHandler:
    @staticmethod
    def sanitize_error(error: Exception, is_production: bool) -> Dict:
        """Sanitize error details for production"""
        if is_production:
            return {
                "error_code": getattr(error, 'code', ErrorCode.INTERNAL_ERROR),
                "message": "An error occurred. Please contact support.",
                "request_id": generate_request_id()
            }
        else:
            return {
                "error_code": getattr(error, 'code', ErrorCode.INTERNAL_ERROR),
                "message": str(error),
                "details": getattr(error, 'details', {}),
                "traceback": traceback.format_exc()
            }


# ============================================================================
# P2 FIX #10: Per-Endpoint Rate Limiting
# ============================================================================

from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@router.post("/execute")
@limiter.limit("10/minute")  # Strict limit on trade execution
async def execute_trade(request: Request, ...):
    """Execute trade with strict rate limiting"""
    pass

@router.get("/history")
@limiter.limit("100/minute")  # More lenient for reads
async def get_trade_history(request: Request, ...):
    """Get trade history"""
    pass


# ============================================================================
# TESTING UTILITIES
# ============================================================================

import pytest
import asyncio

@pytest.mark.asyncio
async def test_concurrent_trade_execution():
    """Test race condition protection"""
    async def execute_concurrent_trades():
        tasks = [
            execute_trade(portfolio_id=1, symbol="AAPL", side="buy", 
                         quantity=10, price=150.0)
            for _ in range(100)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    results = await execute_concurrent_trades()
    
    # Verify no race conditions
    db = next(get_db())
    portfolio = db.query(Portfolio).filter(Portfolio.id == 1).first()
    assert portfolio.balance >= settings.MIN_BALANCE
    
    # Verify all trades are consistent
    trades = db.query(Trade).filter(Trade.portfolio_id == 1).all()
    total_cost = sum(t.quantity * t.price for t in trades)
    assert abs(portfolio.balance - (10000 - total_cost)) < 0.01


def test_price_validation():
    """Test strict price validation"""
    validator = PriceValidator()
    
    # Valid prices
    assert validator.validate_price(100.50) == Decimal("100.50")
    
    # Invalid prices
    with pytest.raises(ValidationError):
        validator.validate_price(-100)
    
    with pytest.raises(ValidationError):
        validator.validate_price(0)
    
    with pytest.raises(ValidationError):
        validator.validate_price(float('inf'))
