"""
Enhanced Trading Engine with Atomic Transaction Handling

Provides transaction-safe trade execution with rollback on failures.
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager

from app.db.models import Portfolio, Position, Trade
from app.core.errors import TradingError, ErrorCode
from app.core.config import settings
from app.core.structured_logging import get_logger

logger = get_logger(__name__)


@contextmanager
def atomic_transaction(db: Session):
    """
    Context manager for atomic database transactions.
    
    Automatically commits on success, rolls back on error.
    
    Usage:
        with atomic_transaction(db):
            # database operations
            pass
    """
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("transaction_rollback", error=str(e), exc_info=True)
        raise


class EnhancedTradingEngine:
    """
    Enhanced trading engine with atomic transactions and comprehensive error handling.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.min_balance = settings.MIN_BALANCE
        self.max_position_size = settings.MAX_POSITION_SIZE
        self.risk_per_trade = settings.RISK_PER_TRADE
    
    def validate_trade(
        self,
        portfolio_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float
    ) -> tuple[bool, str]:
        """
        Validate trade before execution.
        
        Returns: (is_valid, reason)
        """
        # Validate side
        if side not in ['buy', 'sell']:
            return False, "Invalid side: must be 'buy' or 'sell'"
        
        # Validate quantity
        if quantity <= 0:
            return False, "Quantity must be positive"
        
        # Validate price
        if price <= 0:
            return False, "Price must be positive"
        
        # Get portfolio with lock
        portfolio = self.db.query(Portfolio).filter(
            Portfolio.id == portfolio_id
        ).first()
        
        if not portfolio:
            return False, "Portfolio not found"
        
        # Validate balance for buy orders
        if side == 'buy':
            total_cost = quantity * price
            
            # Check sufficient balance
            if portfolio.balance < total_cost:
                return False, f"Insufficient balance: need ${total_cost:.2f}, have ${portfolio.balance:.2f}"
            
            # Check minimum balance protection
            if portfolio.balance - total_cost < self.min_balance:
                return False, f"Trade would violate minimum balance of ${self.min_balance}"
            
            # Check position size limit
            position_value = total_cost
            max_position_value = portfolio.total_value * self.max_position_size
            
            if position_value > max_position_value:
                return False, f"Position size ${position_value:.2f} exceeds limit of ${max_position_value:.2f}"
        
        # Validate sell orders
        if side == 'sell':
            position = self.db.query(Position).filter(
                Position.portfolio_id == portfolio_id,
                Position.symbol == symbol
            ).first()
            
            if not position:
                return False, f"No position found for {symbol}"
            
            if position.quantity < quantity:
                return False, f"Insufficient shares: need {quantity}, have {position.quantity}"
        
        return True, "OK"
    
    def execute_trade(
        self,
        portfolio_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute trade with atomic transaction handling.
        
        Args:
            portfolio_id: Portfolio ID
            symbol: Stock symbol
            side: 'buy' or 'sell'
            quantity: Number of shares
            price: Price per share
            stop_loss_pct: Optional stop-loss percentage
            take_profit_pct: Optional take-profit percentage
            
        Returns:
            Dict with trade details and success status
            
        Raises:
            TradingError: On validation or execution failure
        """
        logger.info(
            "trade_execution_start",
            portfolio_id=portfolio_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price
        )
        
        # Validate trade
        is_valid, reason = self.validate_trade(portfolio_id, symbol, side, quantity, price)
        if not is_valid:
            logger.warning("trade_validation_failed", reason=reason)
            raise TradingError(
                code=ErrorCode.TRADE_VALIDATION_FAILED if 'Invalid' in reason 
                     else ErrorCode.TRADE_INSUFFICIENT_BALANCE if 'balance' in reason.lower()
                     else ErrorCode.TRADE_POSITION_SIZE_EXCEEDED,
                message=reason
            )
        
        # Execute with atomic transaction
        try:
            with atomic_transaction(self.db):
                # Lock portfolio row to prevent race conditions
                portfolio = self.db.query(Portfolio).with_for_update().filter(
                    Portfolio.id == portfolio_id
                ).first()
                
                if not portfolio:
                    raise TradingError(
                        code=ErrorCode.PORTFOLIO_NOT_FOUND,
                        message=f"Portfolio {portfolio_id} not found"
                    )
                
                # Create trade record
                trade = Trade(
                    portfolio_id=portfolio_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price
                )
                
                # Update portfolio balance
                if side == 'buy':
                    total_cost = quantity * price
                    portfolio.balance -= total_cost
                else:  # sell
                    total_proceeds = quantity * price
                    portfolio.balance += total_proceeds
                
                # Update or create position
                position = self.db.query(Position).filter(
                    Position.portfolio_id == portfolio_id,
                    Position.symbol == symbol
                ).first()
                
                if side == 'buy':
                    if position:
                        # Update existing position
                        total_quantity = position.quantity + quantity
                        total_cost = (position.quantity * position.avg_entry_price) + (quantity * price)
                        position.quantity = total_quantity
                        position.avg_entry_price = total_cost / total_quantity
                        position.current_price = price
                    else:
                        # Create new position
                        position = Position(
                            portfolio_id=portfolio_id,
                            symbol=symbol,
                            quantity=quantity,
                            avg_entry_price=price,
                            current_price=price
                        )
                        self.db.add(position)
                    
                    # Set stop-loss and take-profit if provided
                    if stop_loss_pct:
                        position.stop_loss_price = price * (1 - stop_loss_pct)
                    if take_profit_pct:
                        position.take_profit_price = price * (1 + take_profit_pct)
                
                else:  # sell
                    if position:
                        position.quantity -= quantity
                        
                        # Calculate P&L
                        trade.pnl = (price - position.avg_entry_price) * quantity
                        
                        # Remove position if fully closed
                        if position.quantity == 0:
                            self.db.delete(position)
                
                # Update portfolio total value
                total_position_value = sum(
                    p.quantity * p.current_price 
                    for p in self.db.query(Position).filter(
                        Position.portfolio_id == portfolio_id
                    ).all()
                )
                portfolio.total_value = portfolio.balance + total_position_value
                
                # Add trade to database
                self.db.add(trade)
                
                # Transaction will be committed by context manager
                
                logger.info(
                    "trade_executed_successfully",
                    trade_id=trade.id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                    pnl=trade.pnl
                )
                
                return {
                    "success": True,
                    "trade": {
                        "id": trade.id,
                        "symbol": trade.symbol,
                        "side": trade.side,
                        "quantity": trade.quantity,
                        "price": trade.price,
                        "pnl": trade.pnl
                    },
                    "portfolio": {
                        "balance": portfolio.balance,
                        "total_value": portfolio.total_value
                    }
                }
                
        except TradingError:
            raise
        except SQLAlchemyError as e:
            logger.error("database_error", error=str(e), exc_info=True)
            raise TradingError(
                code=ErrorCode.DB_TRANSACTION_FAILED,
                message="Database transaction failed",
                details={"error": str(e)}
            )
        except Exception as e:
            logger.error("unexpected_error", error=str(e), exc_info=True)
            raise TradingError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Unexpected error during trade execution",
                details={"error": str(e)}
            )
