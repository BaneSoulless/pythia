"""TradingModeRouter — selects PaperTradingBroker or AlpacaAdapter.

Based on TRADING_MODE env var. Default: paper (never live by default).
Safety invariant: get_trading_mode() returns 'paper' for any
unrecognized value, ensuring no accidental live trading.
"""
from __future__ import annotations

import os

import structlog

logger = structlog.get_logger("PYTHIA-MODE-ROUTER")

TRADING_MODE_PAPER = "paper"
TRADING_MODE_LIVE = "live"
_ALLOWED_MODES = {TRADING_MODE_PAPER, TRADING_MODE_LIVE}


def get_trading_mode() -> str:
    """Return current trading mode from environment. Defaults to 'paper'."""
    mode = os.getenv("TRADING_MODE", TRADING_MODE_PAPER).lower().strip()
    if mode not in _ALLOWED_MODES:
        logger.warning(
            "invalid_trading_mode",
            value=mode,
            fallback=TRADING_MODE_PAPER,
        )
        return TRADING_MODE_PAPER
    return mode


def is_paper_mode() -> bool:
    """True if current mode is paper trading."""
    return get_trading_mode() == TRADING_MODE_PAPER


def is_live_mode() -> bool:
    """True if current mode is live trading."""
    return get_trading_mode() == TRADING_MODE_LIVE


def get_broker(db_session=None):
    """Return the appropriate broker based on TRADING_MODE.

    NEVER returns AlpacaAdapter unless TRADING_MODE=live is explicit.

    Args:
        db_session: SQLAlchemy session (required for paper mode).

    Returns:
        PaperTradingBroker or AlpacaAdapter instance.
    """
    mode = get_trading_mode()
    logger.info("broker_mode_selected", mode=mode)

    if mode == TRADING_MODE_PAPER:
        from pythia.infrastructure.brokers.paper_trading_broker import (
            PaperTradingBroker,
        )
        return PaperTradingBroker(db_session=db_session)

    # Live — only if explicitly requested
    from pythia.adapters.alpaca_adapter import AlpacaAdapter
    from pythia.core.config import settings

    logger.warning("LIVE_TRADING_MODE_ACTIVE — real money at risk")
    return AlpacaAdapter(
        api_key=getattr(settings, "ALPACA_API_KEY", getattr(settings, "EXCHANGE_API_KEY", "unconfigured")),
        secret_key=getattr(settings, "ALPACA_SECRET_KEY", getattr(settings, "EXCHANGE_SECRET_KEY", "unconfigured")),
        paper=False,
    )


def get_broker_for_asset_class(asset_class: "AssetClass", db_session=None):
    """Returns the correct broker for a given asset class."""
    from pythia.core.asset_class import AssetClass
    if asset_class == AssetClass.PREDICTION_MARKET:
        from pythia.infrastructure.brokers.prediction_market_adapter import (
            PredictionMarketAdapter,
        )
        pm_broker = os.getenv("PM_BROKER", "polymarket")
        return PredictionMarketAdapter(broker=pm_broker)
    # CRYPTO e STOCK: usa il broker standard (Alpaca paper/live)
    return get_broker(db_session=db_session)

