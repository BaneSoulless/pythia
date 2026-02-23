from dataclasses import dataclass
from typing import Optional

@dataclass
class ForexMarket:
    """Domain model for a Forex currency pair."""
    symbol: str  # e.g. "EUR/USD"
    base_currency: str
    quote_currency: str
    pip_value: float = 0.0001
    contract_size: float = 100000  # Standard Lot
    
    def calculate_pip_gain(self, entry_price: float, exit_price: float) -> float:
        """Calculate the number of pips gained/lost."""
        diff = exit_price - entry_price
        # For USD/JPY pips are usually at the 2nd decimal
        divisor = 0.01 if "JPY" in self.symbol else 0.0001
        return diff / divisor

    def calculate_pnl(self, qty_lots: float, entry_price: float, exit_price: float, leverage: int = 1) -> float:
        """Calculate USD PnL for a trade including leverage."""
        pips = self.calculate_pip_gain(entry_price, exit_price)
        # Note: simplistic PnL calculation which assumes quote is USD
        return pips * self.contract_size * qty_lots * self.pip_value

    def get_margin_required(self, price: float, qty_lots: float, leverage: int) -> float:
        """Calculate required margin for a position."""
        notional_value = qty_lots * self.contract_size * price
        return notional_value / leverage
