"""
Stop-Loss and Take-Profit Manager

P0-3 FIX: Atomic transaction handling with row-level locking.
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime
from decimal import Decimal
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import Trade, Portfolio, Position

logger = logging.getLogger(__name__)


@contextmanager
def atomic_transaction(db: Session):
    """
    Context manager for atomic database transactions.
    
    Automatically commits on success, rolls back on error.
    """
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Transaction rolled back: {e}")
        raise


class StopLossTakeProfitManager:
    """
    Manages stop-loss and take-profit orders.
    
    P0-3 FIX: All position closes are now atomic with row-level locking.
    """

    def __init__(
        self,
        db_session: Session,
        default_stop_loss_pct: float = 0.02,  # 2% stop loss
        default_take_profit_pct: float = 0.05,  # 5% take profit
        trailing_stop: bool = False
    ):
        self.db = db_session
        self.default_stop_loss_pct = default_stop_loss_pct
        self.default_take_profit_pct = default_take_profit_pct
        self.trailing_stop = trailing_stop

    def check_all_positions(self) -> List[Dict]:
        """
        Check all open positions for stop-loss or take-profit triggers
        """
        triggered_orders = []
        
        # Fetch all open positions
        positions = self.db.query(Position).filter(Position.status == "open").all()
        
        for position in positions:
            if not position.current_price:
                continue
                
            # Check Stop Loss
            if position.stop_loss_price and position.current_price <= position.stop_loss_price:
                logger.info(f"Stop loss triggered for {position.symbol} at {position.current_price}")
                self._close_position(position, "stop_loss")
                triggered_orders.append({
                    "symbol": position.symbol,
                    "type": "stop_loss",
                    "price": float(position.current_price)
                })
                continue

            # Check Take Profit
            if position.take_profit_price and position.current_price >= position.take_profit_price:
                logger.info(f"Take profit triggered for {position.symbol} at {position.current_price}")
                self._close_position(position, "take_profit")
                triggered_orders.append({
                    "symbol": position.symbol,
                    "type": "take_profit",
                    "price": float(position.current_price)
                })
                continue
                
            # Update Trailing Stop
            if self.trailing_stop and position.trailing_stop_pct:
                self._update_trailing_stop(position)

        return triggered_orders

    def _close_position(self, position: Position, reason: str):
        """
        Close position with full atomicity.
        
        P0-3 FIX: Uses row-level locking and creates Trade record.
        """
        try:
            with atomic_transaction(self.db):
                # Lock position row
                locked_pos = self.db.execute(
                    select(Position)
                    .where(Position.id == position.id)
                    .with_for_update()
                ).scalar_one()
                
                # Calculate PnL
                pnl = (locked_pos.current_price - locked_pos.average_price) * locked_pos.quantity
                
                # Create trade record FIRST (audit trail)
                trade = Trade(
                    portfolio_id=locked_pos.portfolio_id,
                    symbol=locked_pos.symbol,
                    side='sell',
                    quantity=locked_pos.quantity,
                    price=locked_pos.current_price,
                    pnl=pnl,
                    strategy_used=f"auto_{reason}"
                )
                self.db.add(trade)
                
                # Update position status
                locked_pos.status = "closed"
                locked_pos.exit_price = locked_pos.current_price
                locked_pos.exit_date = datetime.utcnow()
                locked_pos.exit_reason = reason
                
                # Update portfolio balance (with lock)
                portfolio = self.db.execute(
                    select(Portfolio)
                    .where(Portfolio.id == locked_pos.portfolio_id)
                    .with_for_update()
                ).scalar_one()
                
                proceeds = locked_pos.quantity * locked_pos.current_price
                portfolio.balance = portfolio.balance + proceeds
                
                logger.info(f"Position {locked_pos.symbol} closed: reason={reason}, pnl={pnl}")
                
        except Exception as e:
            logger.error(f"Stop-loss execution failed for {position.symbol}: {e}", exc_info=True)
            raise


    def _update_trailing_stop(self, position: Position):
        """Update trailing stop price"""
        if not position.trailing_stop_pct:
            return

        # Calculate new stop loss based on current price
        new_stop_loss = position.current_price * (1 - position.trailing_stop_pct)
        
        # Only move stop loss UP (for long positions)
        if not position.stop_loss_price or new_stop_loss > position.stop_loss_price:
            position.stop_loss_price = new_stop_loss
            self.db.commit()

    def set_stop_loss_take_profit(
        self,
        position_id: int,
        stop_loss_pct: float,
        take_profit_pct: float
    ):
        """Set SL/TP for a position"""
        position = self.db.query(Position).filter(Position.id == position_id).first()
        if not position:
            raise ValueError(f"Position {position_id} not found")

        # Assuming entry price is average_price
        entry_price = position.average_price
        
        position.stop_loss_price = entry_price * (1 - stop_loss_pct)
        position.take_profit_price = entry_price * (1 + take_profit_pct)
        self.db.commit()

    def calculate_risk_reward(
        self,
        entry_price: float,
        stop_loss_price: float,
        take_profit_price: float
    ) -> float:
        """Calculate risk/reward ratio"""
        risk = entry_price - stop_loss_price
        reward = take_profit_price - entry_price
        
        if risk <= 0:
            return 0.0
            
        return reward / risk

    def update_trailing_stops(self):
        """Update all trailing stops"""
        positions = self.db.query(Position).filter(Position.status == "open").all()
        for position in positions:
            self._update_trailing_stop(position)
