"""Celery task definitions for Pythia v4.0 workers.

Each task runs in a separate Celery worker process, enabling
horizontal scaling and fault isolation.
"""
import os
import logging
from pythia.infrastructure.celery_app import app

logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    name="pythia.infrastructure.tasks.scan_prediction_markets",
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=280,
    time_limit=300,
)
def scan_prediction_markets(self):
    """Scan Kalshi + Polymarket for cross-platform arbitrage.

    Runs every 5 minutes via Celery Beat.
    Circuit breaker protects against API failures.
    """
    from pythia.adapters.pmxt_adapter import PmxtAdapter
    from pythia.application.trading.arbitrage_detector import ArbitrageDetector
    from pythia.domain.markets.prediction_market import PredictionMarket

    try:
        adapter = PmxtAdapter(
            kalshi_api_key=os.getenv("KALSHI_API_KEY"),
            kalshi_private_key_path=os.getenv("KALSHI_KEY_PATH"),
            polymarket_wallet_key=os.getenv("POLYMARKET_WALLET_KEY"),
        )
        detector = ArbitrageDetector(min_roi=0.015)

        kalshi_raw = adapter.fetch_markets("kalshi", limit=50)
        kalshi_markets = [
            PredictionMarket(
                market_id=m["market_id"],
                description=m["description"],
                yes_price=m["yes_price"],
                no_price=m["no_price"],
                platform="kalshi",
                volume=m.get("volume", 0),
            )
            for m in kalshi_raw
        ]

        poly_markets = []
        if os.getenv("POLYMARKET_WALLET_KEY"):
            poly_raw = adapter.fetch_markets("polymarket", limit=50)
            poly_markets = [
                PredictionMarket(
                    market_id=m["market_id"],
                    description=m["description"],
                    yes_price=m["yes_price"],
                    no_price=m["no_price"],
                    platform="polymarket",
                    volume=m.get("volume", 0),
                )
                for m in poly_raw
            ]

        result = {
            "kalshi_scanned": len(kalshi_markets),
            "polymarket_scanned": len(poly_markets),
            "opportunities": [],
        }

        if poly_markets:
            opportunities = detector.find_opportunities(kalshi_markets, poly_markets)
            result["opportunities"] = [
                {"roi": o["roi"], "strategy": o["strategy"]} for o in opportunities
            ]
            if opportunities:
                logger.info(
                    "Found %d arbitrage opportunities", len(opportunities)
                )

        return result

    except Exception as exc:
        logger.error("PM scan failed: %s", exc)
        raise self.retry(exc=exc)


@app.task(
    bind=True,
    name="pythia.infrastructure.tasks.execute_multi_asset_trade",
    max_retries=2,
    default_retry_delay=5,
    soft_time_limit=25,
    time_limit=30,
)
def execute_multi_asset_trade(self, asset_class: str, symbol: str, side: str, quantity: float):
    """Execute a trade on the appropriate platform.

    Dispatches to the correct adapter based on asset_class.
    Triggered by AI signals or manual commands.
    """
    try:
        logger.info(
            "Executing %s %s %s qty=%.2f", asset_class, side, symbol, quantity
        )

        if asset_class == "stocks":
            from pythia.adapters.alpaca_adapter import AlpacaAdapter
            adapter = AlpacaAdapter(
                api_key=os.getenv("ALPACA_API_KEY", ""),
                secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
            )
            import asyncio
            result = asyncio.run(adapter.place_order(symbol, quantity, side))
            return {"status": "executed", "platform": "alpaca", "result": str(result)}

        if asset_class == "prediction_markets":
            from pythia.adapters.pmxt_adapter import PmxtAdapter
            adapter = PmxtAdapter(
                kalshi_api_key=os.getenv("KALSHI_API_KEY"),
                kalshi_private_key_path=os.getenv("KALSHI_KEY_PATH"),
            )
            result = adapter.place_order("kalshi", symbol, side, quantity, 0.0)
            return {"status": "executed", "platform": "kalshi", "result": str(result)}

        return {"status": "unsupported", "asset_class": asset_class}

    except Exception as exc:
        logger.error("Trade execution failed: %s", exc)
        raise self.retry(exc=exc)


@app.task(
    name="pythia.infrastructure.tasks.generate_ai_signal",
    soft_time_limit=8,
    time_limit=10,
)
def generate_ai_signal(pair: str, price: float, indicators: dict):
    """Generate AI trading signal via Groq LLM.

    Triggered on new candle data. Results are published
    to the event bus for downstream consumption.
    """
    try:
        from pythia.application.ai_providers.groq_client import GroqClient
        import asyncio

        client = GroqClient()
        signal = asyncio.run(
            client.get_signal(
                pair,
                price,
                indicators.get("rsi", 50),
                indicators.get("ema_fast", price),
                indicators.get("ema_slow", price),
            )
        )

        return {
            "pair": pair,
            "action": signal.action,
            "confidence": signal.confidence,
            "reason": signal.reason,
        }

    except Exception as exc:
        logger.error("AI signal generation failed: %s", exc)
        return {"pair": pair, "action": "HOLD", "confidence": 0.0, "error": str(exc)}
