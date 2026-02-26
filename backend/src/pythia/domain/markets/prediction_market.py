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
        """Calculate arbitrage opportunity against another market.

        Checks both directions:
        - Forward: BUY YES on self, BUY NO on other
        - Reverse: BUY NO on self, BUY YES on other
        Returns the better opportunity if either exists.
        """
        opportunities = []

        # Forward: YES self + NO other
        forward_cost = self.yes_price + other.no_price
        if forward_cost < 1.0:
            forward_profit = 1.0 - forward_cost
            opportunities.append({
                "cost": forward_cost,
                "profit": forward_profit,
                "roi": forward_profit / forward_cost,
                "strategy": f"BUY YES on {self.platform}, BUY NO on {other.platform}",
            })

        # Reverse: NO self + YES other
        reverse_cost = self.no_price + other.yes_price
        if reverse_cost < 1.0:
            reverse_profit = 1.0 - reverse_cost
            opportunities.append({
                "cost": reverse_cost,
                "profit": reverse_profit,
                "roi": reverse_profit / reverse_cost,
                "strategy": f"BUY NO on {self.platform}, BUY YES on {other.platform}",
            })

        if not opportunities:
            return None

        return max(opportunities, key=lambda x: x["roi"])
