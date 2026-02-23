from dataclasses import dataclass
from typing import Optional, Literal

@dataclass
class PredictionMarket:
    market_id: str
    description: str
    yes_price: float
    no_price: float
    platform: Literal["polymarket", "kalshi"]
    volume: float

    def implied_probability(self) -> float:
        return self.yes_price

    def arbitrage_opportunity(self, other: 'PredictionMarket') -> Optional[dict]:
        total_cost = self.yes_price + other.no_price

        if total_cost < 1.0:
            profit = 1.0 - total_cost
            return {
                "cost": total_cost,
                "profit": profit,
                "roi": profit / total_cost,
                "strategy": f"BUY YES on {self.platform}, BUY NO on {other.platform}"
            }

        return None
