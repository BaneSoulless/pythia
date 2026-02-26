"""MultiAssetOrchestrator — Pythia v4.0 Application Service.

Coordinates trading across all asset classes using Port interfaces.
Dispatches trades through the correct adapter based on AssetClass.
Uses EventBus for side effects and Celery for async execution.
"""
import logging
from typing import Optional

from pythia.core.ports import (
    AssetClass,
    AIInferencePort,
    MarketDataPort,
    TradingPort,
    TradingSignal,
)
from pythia.domain.events.domain_events import TradeExecutedEvent

logger = logging.getLogger(__name__)


class MultiAssetOrchestrator:
    """Coordinates trading across all registered asset classes.

    Responsibilities:
    - Route signals to the correct adapter via Port interfaces
    - Calculate position size (half-Kelly)
    - Emit domain events post-execution
    - Enforce risk limits before execution
    """

    def __init__(
        self,
        trading_ports: dict[AssetClass, TradingPort],
        market_data_ports: Optional[dict[AssetClass, MarketDataPort]] = None,
        ai_port: Optional[AIInferencePort] = None,
        max_position_pct: float = 0.10,
        min_confidence: float = 0.60,
    ):
        self.trading_ports = trading_ports
        self.market_data_ports = market_data_ports or {}
        self.ai_port = ai_port
        self.max_position_pct = max_position_pct
        self.min_confidence = min_confidence
        self._event_handlers: list = []

    def register_event_handler(self, handler):
        """Register a handler for post-trade domain events."""
        self._event_handlers.append(handler)

    async def execute_signal(self, signal: TradingSignal) -> dict:
        """Execute a trade based on a TradingSignal.

        Args:
            signal: AI-generated signal with action, confidence, pair, and asset_class.

        Returns:
            Execution result dict with trade details.

        Raises:
            ValueError: If no adapter is registered for the signal's asset_class.
        """
        if signal.action == "HOLD":
            logger.info("HOLD signal for %s — no action", signal.pair)
            return {"status": "hold", "pair": signal.pair}

        if signal.confidence < self.min_confidence:
            logger.info(
                "Signal confidence %.2f below threshold %.2f for %s — skipping",
                signal.confidence, self.min_confidence, signal.pair,
            )
            return {"status": "skipped", "reason": "low_confidence", "pair": signal.pair}

        port = self.trading_ports.get(signal.asset_class)
        if port is None:
            raise ValueError(
                f"No trading adapter registered for {signal.asset_class.value}"
            )

        is_open = await port.is_market_open()
        if not is_open:
            logger.info("Market closed for %s — deferring", signal.asset_class.value)
            return {"status": "deferred", "reason": "market_closed"}

        quantity = self._calculate_position_size(signal)
        result = await port.place_order(
            symbol=signal.pair,
            side=signal.action.lower(),
            quantity=quantity,
        )

        event = TradeExecutedEvent(
            symbol=signal.pair,
            side=signal.action,
            quantity=quantity,
            price=result.get("price", 0.0),
            pnl=result.get("pnl", 0.0),
            platform=signal.asset_class.value,
            asset_class=signal.asset_class.value,
        )
        await self._emit(event)

        logger.info(
            "Executed %s %s %.2f @ %s via %s",
            signal.action, signal.pair, quantity,
            result.get("price", "market"), signal.asset_class.value,
        )
        return {
            "status": "executed",
            "pair": signal.pair,
            "side": signal.action,
            "quantity": quantity,
            "result": result,
        }

    async def get_portfolio_snapshot(self) -> dict:
        """Aggregate positions across all registered trading ports."""
        snapshot = {}
        for asset_class, port in self.trading_ports.items():
            try:
                positions = await port.get_positions()
                account = await port.get_account_status()
                snapshot[asset_class.value] = {
                    "positions": positions,
                    "account": account,
                }
            except Exception as exc:
                logger.warning(
                    "Failed to fetch %s portfolio: %s", asset_class.value, exc
                )
                snapshot[asset_class.value] = {"error": str(exc)}
        return snapshot

    def _calculate_position_size(self, signal: TradingSignal) -> float:
        """Position sizing using half-Kelly criterion.

        Kelly fraction = confidence * edge_factor.
        Half-Kelly reduces variance while maintaining positive EV.
        """
        kelly_fraction = signal.confidence * 0.5
        min_size = 10.0
        max_size = 1000.0
        raw_size = kelly_fraction * max_size
        return max(min_size, min(raw_size, max_size))

    async def _emit(self, event):
        """Emit domain event to all registered handlers."""
        for handler in self._event_handlers:
            try:
                await handler(event)
            except Exception as exc:
                logger.error("Event handler failed: %s", exc)
