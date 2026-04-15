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
import yaml
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import ccxt.async_support as ccxt
import pandas as pd
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pythia.adapters.ml_gate import MLMetaGate
from pythia.api.v1.health import router as health_router
from pythia.api.v1.market_data import router as market_data_router
from pythia.api.v1.paper_trading import router as paper_router
from pythia.api.v1.portfolio import router as portfolio_router
from pythia.api.v1.trades import router as trades_router
from pythia.application.asi_evolve import ASIEvolveEngine
from pythia.application.shadow_evaluator import ShadowEvaluator
from pythia.infrastructure.messaging.system_bus import SystemBus
from pythia.infrastructure.monitoring.prometheus_exporter import get_metrics_exporter
from pythia.infrastructure.secrets.secrets_manager import SecretsManager
from ta.momentum import RSIIndicator
from ta.trend import ADXIndicator, EMAIndicator
from ta.volatility import AverageTrueRange

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("PYTHIA-ORCHESTRATOR")


class ConfigUpdateHandler(FileSystemEventHandler):
    """Handles file system events for config hot-reload."""
    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory and "pythia_params.yaml" in event.src_path:
            self.callback()


class DynamicConfigProvider:
    """Manages hot-reloadable trading parameters."""
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.params = {}
        self.load_config()

    def load_config(self):
        """Load YAML configuration from disk."""
        try:
            with open(self.config_path, "r") as f:
                self.params = yaml.safe_load(f)
            logger.info(f"[CONFIG] Loaded parameters from {self.config_path}")
        except Exception as exc:
            logger.error(f"[CONFIG] Failed to load config: {exc}")

    def get(self, key: str, default=None):
        return self.params.get(key, default)


def create_api_app(config_provider: DynamicConfigProvider) -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Pythia AI Trading Bot",
        version="4.0.0",
        description="Multi-asset trading platform with AI-driven signals",
    )
    
    # Store config provider in app state for access from routes
    app.state.config = config_provider

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
    app.include_router(paper_router)

    return app


class PythiaSupervisor:
    """Supervises all Pythia services with graceful shutdown."""

    def __init__(self):
        self.DRY_RUN: bool = os.environ.get("TRADING_MODE", "paper").lower() != "live"
        self.should_exit = False
        self.loop = None
        self.secrets = SecretsManager(allow_key_generation=True)
        self.metrics = get_metrics_exporter()
        
        # Initialize Dynamic Configuration
        config_path = os.path.join(os.getcwd(), "backend", "config", "pythia_params.yaml")
        self.config_provider = DynamicConfigProvider(config_path)
        
        self.api_app = create_api_app(self.config_provider)
        
        # Initialize Messaging & Evolution Engine
        self.bus = SystemBus()
        self.asi_engine = ASIEvolveEngine(event_bus=self.bus, dry_run=self.DRY_RUN)
        
        # Shadow evaluator for parallel evolved-config testing
        self.shadow_evaluator = ShadowEvaluator(asi_engine=self.asi_engine)
        
        # Inject engine into API state for monitoring
        self.api_app.state.asi_engine = self.asi_engine
        
        self.PAPER_TRADING = True  # Forced YOLO paper trading mode

        # Log trading mode from TradingModeRouter
        from pythia.infrastructure.trading_mode_router import get_trading_mode
        trading_mode = get_trading_mode()
        logger.warning(
            "[ORCHESTRATOR] ⚠️ TRADING_MODE=%s | PAPER_TRADING=%s | DRY_RUN=%s",
            trading_mode, self.PAPER_TRADING, self.DRY_RUN,
        )

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

    def _get_current_metrics(self) -> dict:
        """Collect live trading performance metrics for evolution triggering."""
        try:
            # Attempt to read from Prometheus exporter or portfolio state
            return {
                "trade_count": getattr(self.metrics, "total_trades", 0),
                "sharpe": getattr(self.metrics, "sharpe_ratio", 0.0),
                "drawdown": getattr(self.metrics, "current_drawdown", 0.0),
            }
        except Exception:
            return {"trade_count": 0, "sharpe": 0.0, "drawdown": 0.0}

    async def asi_evolve_worker(self):
        """Background worker for autonomous parameter evolution cycles.

        Every 60s:
        1. Tick the cooldown counter
        2. Check should_evolve with live metrics
        3. If triggered, schedule run_cycle in background
        """
        logger.info("[ORCHESTRATOR] Starting ASI-Evolve Optimization Worker...")

        # Initial wait to let other services stabilize
        await asyncio.sleep(60)

        while not self.should_exit:
            try:
                # --- Tick cooldown (60s per iteration) ---
                if self.asi_engine.cooldown_remaining > 0:
                    self.asi_engine.cooldown_remaining = max(
                        0, self.asi_engine.cooldown_remaining - 60
                    )

                # --- Check if evolution is warranted ---
                current_metrics = self._get_current_metrics()
                if (
                    self.asi_engine.cooldown_remaining <= 0
                    and self.asi_engine.should_evolve(current_metrics)
                ):
                    asyncio.ensure_future(self.asi_engine.run_cycle())
                    logger.info(
                        "[ORCHESTRATOR] ASI evolution cycle scheduled — metrics: %s",
                        current_metrics,
                    )

                # Sleep 60s in 1s increments for responsive shutdown
                for _ in range(60):
                    if self.should_exit:
                        break
                    await asyncio.sleep(1)
            except Exception as exc:
                logger.error("[ORCHESTRATOR] ASI-Evolve Worker Error: %s", exc)
                await asyncio.sleep(300)

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
        
        # Start config observer
        observer = Observer()
        handler = ConfigUpdateHandler(self.config_provider.load_config)
        config_dir = os.path.dirname(self.config_provider.config_path)
        observer.schedule(handler, config_dir, recursive=False)
        observer.start()

        try:
            await asyncio.gather(
                self.start_api_server(),
                self.start_metrics(),
                self.prediction_market_worker(),
                self.ml_dry_run_worker(),
                self.asi_evolve_worker(),
            )
        finally:
            observer.stop()
            observer.join()

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
