import logging
import datetime
import pytz
from typing import List, Dict, Any, Optional
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

logger = logging.getLogger("PYTHIA-ALPACA-ADAPTER")

class AlpacaAdapter:
    """Adapter for US Stocks trading via Alpaca API."""
    
    def __init__(self, api_key: str, secret_key: str, paper: bool = True):
        self.client = TradingClient(api_key, secret_key, paper=paper)
        self.timezone = pytz.timezone('US/Eastern')
        logger.info(f"Initialised Alpaca Adapter (Paper: {paper})")

    def is_market_open(self) -> bool:
        """Validate if US markets are currently open (9:30-16:00 EST)."""
        now = datetime.datetime.now(self.timezone)
        # Check if weekday
        if now.weekday() >= 5:
            return False
            
        opening_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
        closing_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return opening_time <= now <= closing_time

    async def get_account_status(self) -> Dict[str, Any]:
        """Fetch account details including buying power and equity."""
        account = self.client.get_account()
        return {
            "equity": float(account.equity),
            "buying_power": float(account.buying_power),
            "daytrade_count": int(account.daytrade_count),
            "pdt_status": account.pattern_day_trader
        }

    def check_pdt_compliance(self) -> bool:
        """
        Verify Pattern Day Trader (PDT) compliance.
        Rule: Equity < $25,000 and 3+ day trades in 5 days.
        """
        acc = self.client.get_account()
        equity = float(acc.equity)
        day_trades = int(acc.daytrade_count)
        
        if equity < 25000 and day_trades >= 3:
            logger.warning(f"PDT Risk: Equity ${equity}, Day Trades {day_trades}")
            return False
        return True

    async def place_order(
        self, 
        symbol: str, 
        qty: float, 
        side: str, 
        order_type: str = "market", 
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute a buy/sell order with PDT and Market Hours guards."""
        
        if not self.is_market_open():
            raise RuntimeError(f"Order rejected: US Markets closed. Current time (EST): {datetime.datetime.now(self.timezone)}")

        if not self.check_pdt_compliance():
            raise RuntimeError("Order rejected: PDT compliance violation.")

        side_enum = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL
        
        if order_type.lower() == "market":
            request = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side_enum,
                time_in_force=TimeInForce.DAY
            )
        else:
            if price is None:
                raise ValueError("Limit price required for limit orders.")
            request = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side_enum,
                limit_price=price,
                time_in_force=TimeInForce.DAY
            )

        order = self.client.submit_order(request)
        logger.info(f"Alpaca {order_type} {side} placed for {symbol}: {order.id}")
        return dict(order)

    async def fetch_positions(self) -> List[Dict[str, Any]]:
        """Fetch current holdings."""
        positions = self.client.get_all_positions()
        return [dict(p) for p in positions]
