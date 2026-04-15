"""
PredictionMarketAdapter: stub for Polymarket/Kalshi integration.
Full implementation deferred to PREDICTION-MARKET-INTEGRATION session.
Currently: raises NotImplementedError with clear guidance.
"""
from __future__ import annotations
import structlog

logger = structlog.get_logger("PYTHIA-PM-ADAPTER")


class PredictionMarketAdapter:
    """
    Placeholder adapter for Prediction Market brokers.
    Supports Polymarket (via CLOB API) and Kalshi (REST API).
    
    TODO (next session):
    - Polymarket CLOB API: https://docs.polymarket.com
    - Kalshi REST API: https://trading-api.kalshi.com/docs
    - Order types: market, limit (odds-based)
    - Position tracking: contracts, not shares
    - Kelly: use kelly_for_prediction_market() from asset_class.py
    """
    
    SUPPORTED_BROKERS = ["polymarket", "kalshi"]

    def __init__(self, broker: str = "polymarket") -> None:
        if broker not in self.SUPPORTED_BROKERS:
            raise ValueError(f"broker must be one of {self.SUPPORTED_BROKERS}")
        self.broker = broker
        logger.warning(
            "prediction_market_adapter_stub",
            broker=broker,
            status="NOT_IMPLEMENTED",
            next_session="PREDICTION-MARKET-INTEGRATION",
        )

    async def place_order(self, *args, **kwargs):
        raise NotImplementedError(
            "PredictionMarketAdapter is a stub. "
            "Implement PREDICTION-MARKET-INTEGRATION session first."
        )

    async def close_position(self, *args, **kwargs):
        raise NotImplementedError(
            "PredictionMarketAdapter is a stub."
        )
