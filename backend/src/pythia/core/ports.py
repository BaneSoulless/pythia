"""Port interfaces for Pythia v4.0 Hexagonal Architecture.

Defines abstract contracts for all external adapters (trading, market data, AI).
Concrete adapters implement these ports to enable pluggable infrastructure.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class AssetClass(str, Enum):
    """Supported asset classes across all trading adapters."""
    CRYPTO = "crypto"
    STOCKS = "stocks"
    FOREX = "forex"
    PREDICTION_MARKETS = "prediction_markets"


@dataclass(frozen=True)
class TradingSignal:
    """Output from AI inference pipeline."""
    action: str  # BUY, SELL, HOLD
    confidence: float  # 0.0 - 1.0
    pair: str
    reasoning: str
    asset_class: AssetClass
    stop_loss_pct: float = 0.02
    timestamp: datetime = field(default_factory=datetime.utcnow)


class TradingPort(ABC):
    """Port for trading adapters (Alpaca, CCXT, pmxt).

    Each concrete adapter must implement all methods.
    Circuit breaker and retry logic are applied at the adapter level.
    """

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
    ) -> dict:
        """Place a trade order. Price=None implies market order."""

    @abstractmethod
    async def get_positions(self) -> list[dict]:
        """Fetch all open positions."""

    @abstractmethod
    async def get_account_status(self) -> dict:
        """Fetch account equity, buying power, and compliance status."""

    @abstractmethod
    async def is_market_open(self) -> bool:
        """Check if the market is currently open for trading."""


class MarketDataPort(ABC):
    """Port for market data feeds."""

    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> dict:
        """Fetch current bid/ask/last price for a symbol."""

    @abstractmethod
    async def fetch_markets(self, limit: int = 100) -> list[dict]:
        """Fetch available markets/contracts."""


class AIInferencePort(ABC):
    """Port for AI/ML inference providers (Groq, ONNX, RL Agent)."""

    @abstractmethod
    async def get_signal(
        self,
        pair: str,
        price: float,
        indicators: dict,
    ) -> TradingSignal:
        """Generate a trading signal from market data and indicators."""
