"""
Abstract interface and mock implementations for Prediction Market (PM) execution.
Provides safe Paper Trading simulation interfaces following ADR-0002/SOTA resilience patterns.
"""

import uuid
from abc import ABC, abstractmethod
from typing import Any

import structlog
from pythia.domain.prediction_markets.models import Question, TradeIntent

logger = structlog.get_logger(__name__)


class AbstractPredictionMarketAdapter(ABC):
    """
    Standard interface for executing trades on Prediction Markets.
    """

    @abstractmethod
    async def fetch_markets(self, category: str | None = None) -> list[Question]:
        """Fetch available markets, optionally filtered by category."""
        ...

    @abstractmethod
    async def get_market(self, market_id: str) -> Question:
        """Fetch details and current odds for a specific market."""
        ...

    @abstractmethod
    async def place_order(
        self,
        intent: TradeIntent,
        allocated_amount: float
    ) -> dict[str, Any]:
        """
        Place an order using a fully sized and risk-checked intent.
        Must return standard receipt including execution price and exchange order ID.
        """
        ...


class MockPolymarketAdapter(AbstractPredictionMarketAdapter):
    """
    A paper-trading implementation for testing intent flows without risking capital
    or encountering blockchain RPC failures.
    """

    def __init__(self, api_key: str = "mock-key", api_secret: str = "mock-secret"):
        self._api_key = api_key
        self._api_secret = api_secret
        self.simulated_markets: dict[str, Question] = {}

    def _sign_payload(self, intent: TradeIntent) -> str:
        """Simulate payload signing using the secret without exposing it."""
        import hashlib
        import json

        payload_str = json.dumps(intent.model_dump(), sort_keys=True)
        signature_material = f"{payload_str}:{self._api_secret}".encode()
        signature = hashlib.sha256(signature_material).hexdigest()
        logger.debug("Simulated signing", redacted_hash=f"{signature[:8]}***")
        return signature

    async def fetch_markets(self, category: str | None = None) -> list[Question]:
        logger.info("Mock PM Adapter: Fetching markets", category=category)
        return list(self.simulated_markets.values())

    async def get_market(self, market_id: str) -> Question:
        logger.info("Mock PM Adapter: Fetching single market", market_id=market_id)
        if market_id in self.simulated_markets:
            return self.simulated_markets[market_id]
        raise ValueError(f"Market {market_id} not found in mock state.")

    async def place_order(
        self,
        intent: TradeIntent,
        allocated_amount: float
    ) -> dict[str, Any]:
        """Simulate an order placement with deterministic JSON output."""
        logger.info(
            "Mock PM Adapter: Placing order",
            market_id=intent.market_id,
            action=intent.action,
            amount=allocated_amount
        )

        # Simulate slippage (paper assumption: perfect fill at market_implied_probability if perfectly liquid)
        fill_price = intent.market_implied_probability
        shares_bought = allocated_amount / fill_price if fill_price > 0 else 0.0

        _signature = self._sign_payload(intent)

        return {
            "order_id": f"mock-ord-{str(uuid.uuid4())[:8]}",
            "market_id": intent.market_id,
            "outcome_id": intent.outcome_id,
            "status": "FILLED",
            "fill_price": fill_price,
            "shares": shares_bought,
            "allocated_amount": allocated_amount,
            "fees_paid": 0.0,
            "transaction_hash": f"0x{uuid.uuid4().hex}"
        }
