"""
Stop-Loss Manager - REFACTORED with Atomic Transaction Safety
Implements: Full atomicity for position closure, proper rollback handling
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select
from contextlib import contextmanager
from pythia.infrastructure.persistence.models import Trade, Portfolio, Position
from pythia.core.errors import TradingError, ErrorCode
logger = logging.getLogger(__name__)

@contextmanager
def atomic_transaction(db: Session):
    """Context manager for atomic database transactions"""
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error('transaction_rollback', error=str(e), exc_info=True)
        raise

class StopLossTakeProfitManager:
    """
    Manages stop-loss and take-profit orders with atomic execution.
    
    SECURITY FIXES APPLIED:
    - Atomic position closure (trade record created BEFORE status update)
    - Proper rollback on failures
    - Support for short positions in trailing stops
    """

    def __init__(self, db_session: Session, default_stop_loss_pct: float=0.02, default_take_profit_pct: float=0.05, trailing_stop: bool=False):
        self.db = db_session
        self.default_stop_loss_pct = default_stop_loss_pct
        self.default_take_profit_pct = default_take_profit_pct
        self.trailing_stop = trailing_stop

    def check_all_positions(self) -> List[Dict]:
        """Check all open positions for stop-loss or take-profit triggers"""
        triggered_orders = []
        positions = self.db.query(Position).filter(Position.status == 'open').all()
        for position in positions:
            if not position.current_price:
                continue
            if position.stop_loss_price and position.current_price <= position.stop_loss_price:
                logger.info(f'Stop loss triggered for {position.symbol} at {position.current_price}')
                try:
                    self._close_position(position, 'stop_loss')
                    triggered_orders.append({'symbol': position.symbol, 'type': 'stop_loss', 'price': position.current_price})
                except Exception as e:
                    logger.error(f'Failed to close position on stop-loss: {e}')
                continue
            if position.take_profit_price and position.current_price >= position.take_profit_price:
                logger.info(f'Take profit triggered for {position.symbol} at {position.current_price}')
                try:
                    self._close_position(position, 'take_profit')
                    triggered_orders.append({'symbol': position.symbol, 'type': 'take_profit', 'price': position.current_price})
                except Exception as e:
                    logger.error(f'Failed to close position on take-profit: {e}')
                continue
            if self.trailing_stop and position.trailing_stop_pct:
                self._update_trailing_stop(position)
        return triggered_orders

    def _close_position(self, position: Position, reason: str):
        """
        Close position with full atomicity.
        
        CRITICAL: Trade record is created BEFORE position status update
        to ensure no orphaned records on failure.
        """
        try:
            with atomic_transaction(self.db):
                locked_position = self.db.execute(select(Position).where(Position.id == position.id).with_for_update()).scalar_one()
                portfolio = self.db.execute(select(Portfolio).where(Portfolio.id == locked_position.portfolio_id).with_for_update()).scalar_one()
                entry_price = Decimal(str(locked_position.average_price))
                exit_price = Decimal(str(locked_position.current_price))
                quantity = Decimal(str(locked_position.quantity))
                pnl = (exit_price - entry_price) * quantity
                trade = Trade(portfolio_id=locked_position.portfolio_id, symbol=locked_position.symbol, side='sell', quantity=float(quantity), price=float(exit_price), pnl=float(pnl))
                self.db.add(trade)
                self.db.flush()
                balance = Decimal(str(portfolio.balance))
                proceeds = quantity * exit_price
                portfolio.balance = float(balance + proceeds)
                locked_position.status = 'closed'
                locked_position.exit_price = float(exit_price)
                locked_position.exit_date = datetime.utcnow()
                locked_position.exit_reason = reason
                total_position_value = sum((Decimal(str(p.quantity)) * Decimal(str(p.current_price)) for p in self.db.query(Position).filter(Position.portfolio_id == portfolio.id, Position.status == 'open', Position.id != locked_position.id).all()))
                portfolio.total_value = float(Decimal(str(portfolio.balance)) + total_position_value)
                logger.info('position_closed', position_id=locked_position.id, symbol=locked_position.symbol, reason=reason, pnl=float(pnl))
        except Exception as e:
            logger.error(f'Position closure failed: {e}', exc_info=True)
            raise TradingError(code=ErrorCode.TRADE_EXECUTION_FAILED, message=f'Failed to close position: {str(e)}')

    def _update_trailing_stop(self, position: Position):
        """
        Update trailing stop price with support for long and short positions.
        
        SECURITY FIX: Correctly handles short positions (inverse logic)
        """
        if not position.trailing_stop_pct:
            return
        try:
            is_long = position.quantity > 0
            current_price = Decimal(str(position.current_price))
            trailing_pct = Decimal(str(position.trailing_stop_pct))
            if is_long:
                new_stop_loss = current_price * (Decimal('1') - trailing_pct)
                if not position.stop_loss_price:
                    position.stop_loss_price = float(new_stop_loss)
                    self.db.commit()
                elif new_stop_loss > Decimal(str(position.stop_loss_price)):
                    position.stop_loss_price = float(new_stop_loss)
                    self.db.commit()
                    logger.info('trailing_stop_updated', position_id=position.id, symbol=position.symbol, new_stop_loss=float(new_stop_loss))
            else:
                new_stop_loss = current_price * (Decimal('1') + trailing_pct)
                if not position.stop_loss_price:
                    position.stop_loss_price = float(new_stop_loss)
                    self.db.commit()
                elif new_stop_loss < Decimal(str(position.stop_loss_price)):
                    position.stop_loss_price = float(new_stop_loss)
                    self.db.commit()
                    logger.info('trailing_stop_updated', position_id=position.id, symbol=position.symbol, new_stop_loss=float(new_stop_loss), direction='short')
        except Exception as e:
            logger.error(f'Trailing stop update failed: {e}')

    def set_stop_loss_take_profit(self, position_id: int, stop_loss_pct: float, take_profit_pct: float):
        """Set SL/TP for a position"""
        position = self.db.query(Position).filter(Position.id == position_id).first()
        if not position:
            raise TradingError(code=ErrorCode.POSITION_NOT_FOUND, message=f'Position {position_id} not found')
        entry_price = Decimal(str(position.average_price))
        sl_pct = Decimal(str(stop_loss_pct))
        tp_pct = Decimal(str(take_profit_pct))
        position.stop_loss_price = float(entry_price * (Decimal('1') - sl_pct))
        position.take_profit_price = float(entry_price * (Decimal('1') + tp_pct))
        self.db.commit()

    def calculate_risk_reward(self, entry_price: float, stop_loss_price: float, take_profit_price: float) -> float:
        """Calculate risk/reward ratio"""
        entry = Decimal(str(entry_price))
        stop = Decimal(str(stop_loss_price))
        target = Decimal(str(take_profit_price))
        risk = entry - stop
        reward = target - entry
        if risk <= 0:
            return 0.0
        return float(reward / risk)

    def update_trailing_stops(self):
        """Update all trailing stops"""
        positions = self.db.query(Position).filter(Position.status == 'open').all()
        for position in positions:
            if position.trailing_stop_pct:
                self._update_trailing_stop(position)