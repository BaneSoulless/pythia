import pmxt
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class PmxtAdapter:
    def __init__(
        self,
        polymarket_wallet_key: Optional[str] = None,
        kalshi_api_key: Optional[str] = None,
        kalshi_private_key_path: Optional[str] = None
    ):
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

    def fetch_markets(self, platform: str, limit: int = 100) -> List[Dict]:
        client = self._get_client(platform)
        markets = client.fetch_markets(limit=limit)
        logger.info(f"✅ Fetched {len(markets)} markets from {platform}")
        return markets

    def place_order(self, platform: str, market_id: str, side: str, amount: float, price: float) -> Dict:
        client = self._get_client(platform)
        order = client.place_order(
            market_id=market_id,
            side=side,
            amount=amount,
            price=price
        )
        logger.info(f"✅ Order placed: {platform} {side} {amount}x @ ${price}")
        return order

    def _get_client(self, platform: str):
        if platform.lower() == "polymarket":
            return self.poly_client
        elif platform.lower() == "kalshi":
            return self.kalshi_client
        else:
            raise ValueError(f"Unsupported platform: {platform}")
