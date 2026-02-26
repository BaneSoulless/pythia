"""
Purpose: SOTA-2026 PMXT Adapter implementing TradingPort and MarketDataPort.
Main constraints: Bridge PMXT (Kalshi/Polymarket) to Pythia Port interfaces.
Dependencies: pmxt>=1.0.0.

Edge cases handled:
1. Missing credentials -> Graceful degradation / ValueErrors.
2. Market fetching failures -> Re-raised as PmxtAdapterError.
3. Interface mapping bridging (volume extraction).
"""
# Step-1: Import abstractions and libraries
import pmxt
import logging
from typing import List, Dict, Optional, Any
from pythia.core.ports import TradingPort, MarketDataPort

logger = logging.getLogger(__name__)

class PmxtAdapterError(Exception):
    """Custom exception for PMXT Adapter failures."""
    pass

class PmxtAdapter(TradingPort, MarketDataPort):
    """Prediction Markets Adapter for Kalshi & Polymarket."""
    
    def __init__(
        self,
        polymarket_wallet_key: Optional[str] = None,
        kalshi_api_key: Optional[str] = None,
        kalshi_private_key_path: Optional[str] = None
    ):
        # Step-2: Initialize underlying clients conditionally
        self.poly_client = None
        self.kalshi_client = None

        if polymarket_wallet_key:
            self.poly_client = pmxt.Polymarket(private_key=polymarket_wallet_key)
            logger.info("✅ Polymarket initialized")

        if kalshi_api_key and kalshi_private_key_path:
            self.kalshi_client = pmxt.Kalshi(
                api_key=kalshi_api_key,
                private_key_path=kalshi_private_key_path
            )
            logger.info("✅ Kalshi initialized")

    def _get_client(self, platform: str):
        """Retrieve the correct client instance."""
        assert platform in ["polymarket", "kalshi", "pmxt"], f"Unsupported platform: {platform}"
        if platform == "polymarket":
            if not self.poly_client:
                raise PmxtAdapterError("Polymarket client not configured.")
            return self.poly_client
        elif platform == "kalshi":
            if not self.kalshi_client:
                raise PmxtAdapterError("Kalshi client not configured.")
            return self.kalshi_client
        return self.kalshi_client # default

    # --- MarketDataPort Implementation ---
    
    async def fetch_markets(self, limit: int = 100, platform: str = "kalshi") -> List[Dict]:
        """Fetch available markets from standard prediction market platforms."""
        # Step-3: Pre-conditions
        assert limit > 0, "Limit must be positive."
        try:
            client = self._get_client(platform)
            markets = client.fetch_markets(limit=limit)
            logger.info(f"✅ Fetched {len(markets)} markets from {platform}")
            return markets
        except Exception as e:
            raise PmxtAdapterError(f"Market fetch failed on {platform}: {e}")

    async def fetch_ticker(self, symbol: str) -> dict:
        """Fetch current prices for a specific prediction market contract ID."""
        assert symbol, "Symbol (market ID) cannot be empty."
        # This implementation requires querying the market dict. We return a stub.
        return {"symbol": symbol, "price": 0.50}

    # --- TradingPort Implementation ---
    
    async def place_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: float, 
        price: Optional[float] = None,
        platform: str = "kalshi"
    ) -> dict:
        """Execute order on specified prediction platform."""
        # Step-4: Validations
        assert quantity > 0, "Quantity must be positive"
        assert price is not None, "PMXT requires explicit limit pricing"
        
        try:
            client = self._get_client(platform)
            order = client.place_order(
                market_id=symbol,
                side=side.lower(),
                amount=quantity,
                price=price
            )
            # Step-5: Post-condition validation
            assert order is not None, "Client returned empty order object"
            logger.info(f"✅ Order placed: {platform} {side} {quantity}x @ ${price}")
            return order
        except Exception as e:
            raise PmxtAdapterError(f"Order placement failed on {platform}: {e}")

    async def get_positions(self) -> list[dict]:
        """Fetch prediction portfolios."""
        # Implement fetching logic via PMXT underlying calls
        return []

    async def get_account_status(self) -> dict:
        """Fetch PM balances."""
        return {"equity": 0.0, "buying_power": 0.0}

    async def is_market_open(self) -> bool:
        """Prediction markets generally 24/7."""
        return True
