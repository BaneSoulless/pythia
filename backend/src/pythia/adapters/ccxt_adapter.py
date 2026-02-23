import ccxt.async_support as ccxt
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("PYTHIA-CCXT-ADAPTER")

class CCXTForexAdapter:
    """Adapter for Forex trading using CCXT (e.g., Oanda)."""
    
    def __init__(self, exchange_id: str = 'oanda', config: Optional[Dict[str, Any]] = None):
        self.exchange_id = exchange_id
        # In a real scenario, API keys would be in the config or env
        self.config = config or {}
        self.exchange = getattr(ccxt, exchange_id)(self.config)
        self.max_leverage = 30 # Default for many jurisdictions

    async def initialize(self):
        """Perform async initialization if required by CCXT."""
        # Some exchanges might need to fetch markets first
        await self.exchange.load_markets()
        logger.info(f"Initialized CCXT Forex exchange: {self.exchange_id}")

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch current bid/ask price."""
        return await self.exchange.fetch_ticker(symbol)

    async def fetch_balance(self) -> Dict[str, Any]:
        """Fetch account balance details."""
        return await self.exchange.fetch_balance()

    async def create_order(
        self, 
        symbol: str, 
        order_type: str, 
        side: str, 
        amount: float, 
        price: Optional[float] = None,
        leverage: int = 1
    ) -> Dict[str, Any]:
        """Place a forex order with leverage management."""
        if leverage > self.max_leverage:
            raise ValueError(f"Leverage {leverage} exceeds maximum allowed ({self.max_leverage})")
            
        # Oanda-specific or standard CCXT creation
        try:
            params = {'leverage': leverage} if leverage > 1 else {}
            order = await self.exchange.create_order(symbol, order_type, side, amount, price, params)
            logger.info(f"Placed {side} order for {symbol} on {self.exchange_id}")
            return order
        except Exception as e:
            logger.error(f"Error creating order on {self.exchange_id}: {e}")
            raise

    async def get_swap_rates(self, symbol: str) -> Dict[str, float]:
        """Fetch overnight swap rates (long/short) for a symbol."""
        # Note: Not all CCXT exchanges expose swap rates directly in a unified way.
        # This is a placeholder for custom implementation or exchange-specific fetch.
        market = self.exchange.market(symbol)
        info = market.get('info', {})
        
        # Example for Oanda-like structure
        long_swap = float(info.get('long_swap', 0.0))
        short_swap = float(info.get('short_swap', 0.0))
        
        return {
            "long": long_swap,
            "short": short_swap
        }

    async def close(self):
        """Close the exchange session."""
        await self.exchange.close()
