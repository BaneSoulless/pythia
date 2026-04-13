"""Pythia v4.0 Orchestrator (Supervisor).

Manages all backend services as concurrent asyncio tasks:
1. FastAPI API server (:8000) — REST endpoints + health check
2. Prometheus Exporter (:9090) — metrics server
3. Freqtrade Strategy (thread) — crypto trading
4. Streamlit UI (:8501) — control plane dashboard
5. Prediction Market Worker — arbitrage scanner (5min interval)
"""

import asyncio
import logging
import os
import signal
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pythia.api.v1.health import router as health_router
from pythia.api.v1.market_data import router as market_data_router
from pythia.api.v1.portfolio import router as portfolio_router
from pythia.api.v1.trades import router as trades_router
from pythia.infrastructure.monitoring.prometheus_exporter import get_metrics_exporter
from pythia.infrastructure.secrets.secrets_manager import SecretsManager
import ccxt.async_support as ccxt
from pythia.adapters.ml_gate import MLMetaGate
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, ADXIndicator
from ta.volatility import AverageTrueRange

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("PYTHIA-ORCHESTRATOR")


def create_api_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Pythia AI Trading Bot",
        version="4.0.0",
        description="Multi-asset trading platform with AI-driven signals",
    )

    # Enable CORS for local Vite dashboard
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(trades_router, prefix="/api/v1/trades", tags=["trades"])
    app.include_router(portfolio_router, prefix="/api/v1/portfolio", tags=["portfolio"])
    app.include_router(
        market_data_router, prefix="/api/v1/market-data", tags=["market-data"]
    )

    return app


class PythiaSupervisor:
    """Supervises all Pythia services with graceful shutdown."""

    def __init__(self):
        self.should_exit = False
        self.loop = None
        self.secrets = SecretsManager(allow_key_generation=True)
        self.metrics = get_metrics_exporter()
        self.api_app = create_api_app()
        self.PAPER_TRADING = True  # Forced YOLO paper trading mode
        self.DRY_RUN = True
        logger.warning("[ORCHESTRATOR] ⚠️ PAPER_TRADING / DRY_RUN mode ENABLED. No real orders will be placed.")

    def _load_secrets(self):
        """Load encrypted secrets into environment variables."""
        try:
            self.secrets.load_encrypted_env()
            logger.info("[ORCHESTRATOR] Secrets loaded from encrypted environment")
        except FileNotFoundError:
            logger.warning(
                "[ORCHESTRATOR] No encrypted env found, falling back to plaintext"
            )

    async def start_api_server(self):
        """Launch FastAPI via uvicorn as an asyncio task."""
        logger.info("[ORCHESTRATOR] Starting FastAPI server on :8000...")
        config = uvicorn.Config(
            self.api_app,
            host=os.environ.get("BIND_HOST", "127.0.0.1"),
            port=8000,
            log_level="info",
            access_log=False,
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def start_metrics(self):
        """Launch Prometheus exporter."""
        logger.info("[ORCHESTRATOR] Starting Prometheus Exporter on :9090...")
        try:
            self.metrics.start()
            logger.info("[ORCHESTRATOR] Prometheus metrics server started on :9090")
        except OSError as exc:
            logger.error("[ORCHESTRATOR] Failed to start metrics server: %s", exc)

    async def prediction_market_worker(self):
        """Background worker for prediction market arbitrage scanning."""
        logger.info("[ORCHESTRATOR] Starting Prediction Market Arbitrage Worker...")
        from pythia.adapters.pmxt_adapter import PmxtAdapter
        from pythia.application.trading.arbitrage_detector import ArbitrageDetector
        from pythia.domain.markets.prediction_market import PredictionMarket

        adapter = PmxtAdapter(
            kalshi_api_key=os.getenv("KALSHI_API_KEY"),
            kalshi_private_key_path=os.getenv("KALSHI_PRIVATE_KEY_PATH"),
        )
        detector = ArbitrageDetector(min_roi=0.015)

        while not self.should_exit:
            try:
                logger.debug("[ORCHESTRATOR] Scanning prediction markets...")

                kalshi_raw = await adapter.fetch_markets(limit=50, platform="kalshi")
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
                self.metrics.record_markets_scanned("kalshi", len(kalshi_markets))

                poly_markets = []
                if os.getenv("POLYMARKET_WALLET_KEY"):
                    poly_raw = await adapter.fetch_markets(
                        limit=50, platform="polymarket"
                    )
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
                    self.metrics.record_markets_scanned("polymarket", len(poly_markets))

                if poly_markets:
                    opportunities = detector.find_opportunities(
                        kalshi_markets, poly_markets
                    )
                    if opportunities:
                        logger.info(
                            "[ORCHESTRATOR] Found %d arbitrage opportunities",
                            len(opportunities),
                        )

                await asyncio.sleep(300)
            except Exception as exc:
                logger.error("[ORCHESTRATOR] PM Worker Error: %s", exc)
                await asyncio.sleep(30)

    async def ml_dry_run_worker(self):
        """Background worker for ML MetaGate dry-run and data ingestion."""
        logger.info("[ORCHESTRATOR] Starting ML Meta-Labeling Dry-Run Worker...")
        exchange = ccxt.binance({'enableRateLimit': True})
        ml_gate = MLMetaGate()
        symbols = ['BTC/USDT', 'ETH/USDT']
        
        while not self.should_exit:
            try:
                for symbol in symbols:
                    logger.debug(f"[ORCHESTRATOR] Fetching 30d OHLCV for {symbol}...")
                    # 1h candles, 30 days = 720 candles
                    since = exchange.milliseconds() - 30 * 24 * 60 * 60 * 1000
                    ohlcv = await exchange.fetch_ohlcv(symbol, timeframe='1h', since=since, limit=1000)
                    
                    if not ohlcv:
                        continue
                        
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    
                    # Compute required features using `ta` lib
                    df['rsi'] = RSIIndicator(close=df['close'], window=14).rsi()
                    df['ema_fast'] = EMAIndicator(close=df['close'], window=9).ema_indicator()
                    df['ema_slow'] = EMAIndicator(close=df['close'], window=21).ema_indicator()
                    
                    adx = ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=14)
                    df['adx_14'] = adx.adx()
                    
                    atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14)
                    df['atr_volatility'] = atr.average_true_range()
                    
                    df['volume_sma'] = df['volume'].rolling(window=20).mean()
                    df['volume_sma_ratio'] = df['volume'] / df['volume_sma']
                    
                    # Drop NAs computed by TA
                    df.dropna(inplace=True)
                    
                    # Run it through MLMetaGate
                    df = ml_gate.filter_signals(df)
                    
                    # Fetch signals where enter_long == 1
                    signals = df[df['enter_long'] == 1]
                    logger.info(f"[ML-GATE] {symbol}: Found {len(signals)} filtered long signals in the last 30 days.")
                    
                    # Record the latest valid signal confidence to Prometheus
                    if not signals.empty:
                        latest_confidence = signals.iloc[-1]['ml_confidence']
                        self.metrics.record_ml_signal(symbol, float(latest_confidence))
                        logger.info(f"[PROMETHEUS] Injected ML confidence for {symbol}: {latest_confidence:.4f}")
                        
                # Wait 10 minutes before polling new candles
                await asyncio.sleep(600)
            except Exception as exc:
                logger.error("[ORCHESTRATOR] ML Dry-Run Error: %s", exc)
                await asyncio.sleep(60)
        
        await exchange.close()

    async def run(self):
        """Start all services concurrently."""
        self._load_secrets()
        self.loop = asyncio.get_running_loop()

        # Signal handlers (SIGTERM not available on Windows)
        if sys.platform != "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                self.loop.add_signal_handler(
                    sig, lambda: asyncio.create_task(self.shutdown())
                )

        logger.info("[ORCHESTRATOR] Pythia v4.0 — Starting central services...")
        await asyncio.gather(
            self.start_api_server(),
            self.start_metrics(),
            self.prediction_market_worker(),
            self.ml_dry_run_worker(),
        )

    async def shutdown(self):
        """Graceful shutdown of all managed processes."""
        logger.info("[ORCHESTRATOR] Initiating graceful shutdown...")
        self.should_exit = True
        logger.info("[ORCHESTRATOR] Pythia services stopped")
        sys.exit(0)


if __name__ == "__main__":
    supervisor = PythiaSupervisor()
    try:
        asyncio.run(supervisor.run())
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        logger.critical("[ORCHESTRATOR] Operational Failure: %s", exc)
        sys.exit(1)
