"""
Modular Core - Execution Layer
Paper Trading Connector with Calibrated Position Sizing & PnL Tracking
"""
import logging
import asyncio
import sys
import os
import json
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

# Inject Backend Path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backend"))

from app.db.database import SessionLocal
from app.db.models import Trade, User, Portfolio, Position

logger = logging.getLogger("ExecutionConnector")

# Load Paper Trading Config
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
with open(CONFIG_PATH, "r") as f:
    _config = json.load(f)

PAPER_TRADING = _config.get("paper_trading", {})
INITIAL_BALANCE = Decimal(str(PAPER_TRADING.get("initial_balance", 1000.0)))
MAX_POSITION_PCT = Decimal(str(PAPER_TRADING.get("max_position_size_pct", 0.1)))
COMMISSION_RATE = Decimal(str(PAPER_TRADING.get("commission_rate", 0.001)))

class ExchangeConnector:
    """Paper Trading Connector with Strict Capital Constraints"""
    
    def __init__(self, config):
        self.config = config
        self.db = SessionLocal()
        self._portfolio_cache = None
        
    def _get_or_create_portfolio(self, user_id) -> Portfolio:
        if self._portfolio_cache:
            return self._portfolio_cache
            
        port = self.db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
        if not port:
            port = Portfolio(
                user_id=user_id, 
                name="Paper Trading Portfolio",
                balance=INITIAL_BALANCE,
                total_value=INITIAL_BALANCE
            )
            self.db.add(port)
            self.db.commit()
            self.db.refresh(port)
        self._portfolio_cache = port
        return port

    def _get_admin_user(self) -> User:
        return self.db.query(User).filter(User.username == "admin").first()

    def _calculate_position_size(self, portfolio: Portfolio, price: Decimal) -> Decimal:
        """Calculate position size based on max 10% of portfolio"""
        max_capital = portfolio.balance * MAX_POSITION_PCT
        quantity = (max_capital / price).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
        return quantity

    def _calculate_pnl(self, portfolio_id: int) -> dict:
        """Calculate Realized and Unrealized PnL"""
        trades = self.db.query(Trade).filter(Trade.portfolio_id == portfolio_id).all()
        
        realized_pnl = Decimal("0.0")
        for trade in trades:
            if trade.pnl:
                realized_pnl += trade.pnl
        
        # For unrealized, we'd need current positions and live prices
        # Simplified: just return realized for now
        return {
            "realized_pnl": float(realized_pnl),
            "unrealized_pnl": 0.0,  # TODO: Implement with live price feed
            "total_trades": len(trades)
        }

    async def execute_order(self, signal: dict) -> dict:
        """
        Execute paper trade with calibrated position sizing.
        signal: {action, confidence, symbol, current_price...}
        """
        action = signal.get('action')
        symbol = signal.get('symbol', 'BTCUSDT')
        confidence = signal.get('confidence', 0.0)
        current_price = Decimal(str(signal.get('current_price', 50000.0)))
        
        logger.info(f"⚡ PAPER TRADE: {action.upper()} {symbol} @ {current_price} (Conf: {confidence:.2f})")
        
        # Simulate Network Latency
        await asyncio.sleep(0.05)
        
        try:
            user = self._get_admin_user()
            if not user:
                logger.error("Execution Failed: Admin user not found")
                return {"status": "failed", "reason": "no_user"}

            portfolio = self._get_or_create_portfolio(user.id)
            
            # Calculate calibrated position size
            quantity = self._calculate_position_size(portfolio, current_price)
            if quantity <= 0:
                logger.warning("Insufficient balance for trade")
                return {"status": "rejected", "reason": "insufficient_balance"}
            
            # Calculate cost with commission
            gross_cost = current_price * quantity
            commission = gross_cost * COMMISSION_RATE
            total_cost = gross_cost + commission
            
            # Validate balance
            if action == 'buy' and portfolio.balance < total_cost:
                logger.warning(f"Balance {portfolio.balance} < Cost {total_cost}")
                return {"status": "rejected", "reason": "insufficient_balance"}
            
            # Create Trade Record
            trade = Trade(
                portfolio_id=portfolio.id,
                symbol=symbol,
                side=action,
                quantity=quantity,
                price=current_price,
                commission=commission,
                ai_confidence=confidence,
                strategy_used="Sovereign-RL-v5",
                executed_at=datetime.utcnow()
            )
            
            self.db.add(trade)
            
            # Update Balance
            if action == 'buy':
                portfolio.balance -= total_cost
            elif action == 'sell':
                portfolio.balance += (gross_cost - commission)
                
            # Update total value (simplified)
            portfolio.total_value = portfolio.balance
            
            self.db.commit()
            self.db.refresh(trade)
            
            # Calculate PnL for telemetry
            pnl_data = self._calculate_pnl(portfolio.id)
            
            logger.info(f"✅ PAPER TRADE FILLED: ID {trade.id} | Qty: {quantity} | Cost: {total_cost}")
            logger.info(f"📊 PORTFOLIO: Balance={portfolio.balance} | PnL={pnl_data['realized_pnl']}")
            
            return {
                "status": "filled", 
                "trade_id": trade.id, 
                "price": str(current_price),
                "quantity": str(quantity),
                "commission": str(commission),
                "balance": str(portfolio.balance),
                "pnl": pnl_data
            }
            
        except Exception as e:
            logger.error(f"Execution Error: {e}")
            self.db.rollback()
            return {"status": "error", "details": str(e)}

    def get_portfolio_status(self) -> dict:
        """Get current portfolio status for telemetry"""
        user = self._get_admin_user()
        if not user:
            return {"error": "no_user"}
        portfolio = self._get_or_create_portfolio(user.id)
        pnl = self._calculate_pnl(portfolio.id)
        return {
            "balance": float(portfolio.balance),
            "total_value": float(portfolio.total_value),
            "initial_balance": float(INITIAL_BALANCE),
            "pnl": pnl
        }
