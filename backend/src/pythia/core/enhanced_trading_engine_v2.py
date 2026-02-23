"""
Enhanced Trading Engine - REFACTORED with P0 Security Fixes
Implements: Race condition protection, Decimal precision, strict validation
"""
import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from contextlib import contextmanager
from pythia.infrastructure.persistence.models import Portfolio, Position, Trade
from pythia.core.errors import TradingError, ErrorCode
from pythia.core.config import settings
from pythia.core.structured_logging import get_logger
from pythia.core.validators import PriceValidator, QuantityValidator, SymbolValidator
logger = get_logger(__name__)

@contextmanager
def atomic_trade_lock(db: Session, portfolio_id: int):
    """
    Acquire exclusive lock on portfolio with NOWAIT to prevent race conditions.
    Raises TradingError immediately if lock cannot be acquired.
    """
    try:
        portfolio = db.execute(select(Portfolio).where(Portfolio.id == portfolio_id).with_for_update(nowait=True)).scalar_one()
        yield portfolio
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error('trade_lock_failed', portfolio_id=portfolio_id, error=str(e))
        raise TradingError(code=ErrorCode.DB_TRANSACTION_FAILED, message='Concurrent trade detected - please retry', details={'portfolio_id': portfolio_id})

class EnhancedTradingEngine:
    """Enhanced trading engine with atomic transactions and Decimal precision"""

    def __init__(self, db: Session):
        self.db = db
        self.min_balance = Decimal(str(settings.MIN_BALANCE))
        self.max_position_size = Decimal(str(settings.MAX_POSITION_SIZE))
        self.risk_per_trade = Decimal(str(settings.RISK_PER_TRADE))
        self.max_positions = getattr(settings, 'MAX_POSITIONS_PER_PORTFOLIO', 50)

    def validate_trade(self, portfolio_id: int, symbol: str, side: str, quantity: float, price: float) -> tuple[bool, str]:
        """Validate trade with strict type checking and Decimal precision"""
        if side not in ['buy', 'sell']:
            return (False, f'Invalid side: {side}')
        try:
            symbol = SymbolValidator.validate(symbol)
            price_decimal = PriceValidator.validate(price)
            quantity_decimal = QuantityValidator.validate(quantity)
        except TradingError as e:
            return (False, e.message)
        portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if not portfolio:
            return (False, 'Portfolio not found')
        balance = Decimal(str(portfolio.balance))
        if side == 'buy':
            total_cost = quantity_decimal * price_decimal
            if balance < total_cost:
                return (False, f'Insufficient balance: need {total_cost}, have {balance}')
            if balance - total_cost < self.min_balance:
                return (False, f'Trade would violate minimum balance of {self.min_balance}')
            portfolio_value = Decimal(str(portfolio.total_value))
            max_position_value = portfolio_value * self.max_position_size
            if total_cost > max_position_value:
                return (False, f'Position size {total_cost} exceeds limit of {max_position_value}')
            position_count = self.db.query(Position).filter(Position.portfolio_id == portfolio_id, Position.status == 'open').count()
            existing_position = self.db.query(Position).filter(Position.portfolio_id == portfolio_id, Position.symbol == symbol, Position.status == 'open').first()
            if not existing_position and position_count >= self.max_positions:
                return (False, f'Maximum positions limit reached: {self.max_positions}')
        if side == 'sell':
            position = self.db.query(Position).filter(Position.portfolio_id == portfolio_id, Position.symbol == symbol, Position.status == 'open').first()
            if not position:
                return (False, f'No position found for {symbol}')
            position_qty = Decimal(str(position.quantity))
            if position_qty < quantity_decimal:
                return (False, f'Insufficient shares: need {quantity_decimal}, have {position_qty}')
        return (True, 'OK')

    def execute_trade(self, portfolio_id: int, symbol: str, side: str, quantity: float, price: float, stop_loss_pct: Optional[float]=None, take_profit_pct: Optional[float]=None) -> Dict[str, Any]:
        """
        Execute trade with atomic locking and Decimal precision.
        
        SECURITY FIXES APPLIED:
        - Race condition protection via SELECT FOR UPDATE NOWAIT
        - Decimal precision for all financial calculations
        - Strict input validation
        """
        logger.info('trade_execution_start', portfolio_id=portfolio_id, symbol=symbol, side=side, quantity=quantity, price=price)
        is_valid, reason = self.validate_trade(portfolio_id, symbol, side, quantity, price)
        if not is_valid:
            logger.warning('trade_validation_failed', reason=reason)
            raise TradingError(code=ErrorCode.TRADE_VALIDATION_FAILED, message=reason)
        price_decimal = PriceValidator.validate(price)
        quantity_decimal = QuantityValidator.validate(quantity)
        symbol = SymbolValidator.validate(symbol)
        try:
            with atomic_trade_lock(self.db, portfolio_id) as portfolio:
                trade = Trade(portfolio_id=portfolio_id, symbol=symbol, side=side, quantity=float(quantity_decimal), price=float(price_decimal))
                balance = Decimal(str(portfolio.balance))
                if side == 'buy':
                    total_cost = quantity_decimal * price_decimal
                    portfolio.balance = float(balance - total_cost)
                else:
                    total_proceeds = quantity_decimal * price_decimal
                    portfolio.balance = float(balance + total_proceeds)
                position = self.db.query(Position).filter(Position.portfolio_id == portfolio_id, Position.symbol == symbol, Position.status == 'open').first()
                if side == 'buy':
                    if position:
                        pos_qty = Decimal(str(position.quantity))
                        pos_avg = Decimal(str(position.average_price))
                        total_quantity = pos_qty + quantity_decimal
                        total_cost = pos_qty * pos_avg + quantity_decimal * price_decimal
                        position.quantity = float(total_quantity)
                        position.average_price = float(total_cost / total_quantity)
                        position.current_price = float(price_decimal)
                    else:
                        position = Position(portfolio_id=portfolio_id, symbol=symbol, quantity=float(quantity_decimal), average_price=float(price_decimal), current_price=float(price_decimal), status='open')
                        self.db.add(position)
                    if stop_loss_pct:
                        position.stop_loss_price = float(price_decimal * (Decimal('1') - Decimal(str(stop_loss_pct))))
                    if take_profit_pct:
                        position.take_profit_price = float(price_decimal * (Decimal('1') + Decimal(str(take_profit_pct))))
                elif position:
                    pos_qty = Decimal(str(position.quantity))
                    pos_avg = Decimal(str(position.average_price))
                    position.quantity = float(pos_qty - quantity_decimal)
                    pnl = (price_decimal - pos_avg) * quantity_decimal
                    trade.pnl = float(pnl)
                    if position.quantity <= 0.0001:
                        position.status = 'closed'
                total_position_value = sum((Decimal(str(p.quantity)) * Decimal(str(p.current_price)) for p in self.db.query(Position).filter(Position.portfolio_id == portfolio_id, Position.status == 'open').all()))
                portfolio.total_value = float(Decimal(str(portfolio.balance)) + total_position_value)
                self.db.add(trade)
                logger.info('trade_executed_successfully', trade_id=trade.id, symbol=symbol, side=side, quantity=float(quantity_decimal), price=float(price_decimal), pnl=trade.pnl)
                return {'success': True, 'trade': {'id': trade.id, 'symbol': trade.symbol, 'side': trade.side, 'quantity': trade.quantity, 'price': trade.price, 'pnl': trade.pnl}, 'portfolio': {'balance': portfolio.balance, 'total_value': portfolio.total_value}}
        except TradingError:
            raise
        except SQLAlchemyError as e:
            logger.error('database_error', error=str(e), exc_info=True)
            raise TradingError(code=ErrorCode.DB_TRANSACTION_FAILED, message='Database transaction failed', details={'error': str(e)})
        except Exception as e:
            logger.error('unexpected_error', error=str(e), exc_info=True)
            raise TradingError(code=ErrorCode.INTERNAL_ERROR, message='Unexpected error during trade execution', details={'error': str(e)})