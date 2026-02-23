import logging
from typing import List, Dict
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class ArbitrageDetector:
    def __init__(self, min_roi: float = 0.01):
        self.min_roi = min_roi

    def find_opportunities(self, kalshi_markets, polymarket_markets) -> List[Dict]:
        opportunities = []

        for k_market in kalshi_markets:
            for p_market in polymarket_markets:
                if self._markets_match(k_market, p_market):
                    arb = k_market.arbitrage_opportunity(p_market)

                    if arb and arb["roi"] >= self.min_roi:
                        opportunities.append(arb)
                        logger.info(f"🎯 Arbitrage: {arb['roi']*100:.2f}% ROI")

        return opportunities

    def _markets_match(self, market1, market2) -> bool:
        desc1 = market1.description.lower().strip()
        desc2 = market2.description.lower().strip()
        similarity = SequenceMatcher(None, desc1, desc2).ratio()
        return similarity > 0.8
