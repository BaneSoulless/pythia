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
import subprocess
import os
import signal
import sys
import threading

import uvicorn
from fastapi import FastAPI

from pythia.api.v1.health import router as health_router
from pythia.infrastructure.monitoring.prometheus_exporter import get_metrics_exporter
from pythia.infrastructure.secrets.secrets_manager import SecretsManager
from pythia.adapters.freqtrade_adapter import FreqtradeStrategy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("PYTHIA-ORCHESTRATOR")

from fastapi.middleware.cors import CORSMiddleware
from pythia.api.v1.trades import router as trades_router
from pythia.api.v1.portfolio import router as portfolio_router
from pythia.api.v1.market_data import router as market_data_router
from pythia.api.v1.health import router as health_router

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
    app.include_router(market_data_router, prefix="/api/v1/market-data", tags=["market-data"])
    
    return app

class PythiaSupervisor:
    """Supervises all Pythia services with graceful shutdown."""

    def __init__(self):
        self.processes: list[subprocess.Popen] = []
        self.should_exit = False
        self.loop = None
        self.secrets = SecretsManager(allow_key_generation=True)
        self.metrics = get_metrics_exporter()
        self.api_app = create_api_app()

    def _load_secrets(self):
        """Load encrypted secrets into environment variables."""
        try:
            self.secrets.load_encrypted_env()
            logger.info("[ORCHESTRATOR] Secrets loaded from encrypted environment")
        except FileNotFoundError:
            logger.warning("[ORCHESTRATOR] No encrypted env found, falling back to plaintext")

    def _run_freqtrade_sync(self):
        """Run Freqtrade in a thread (blocking API)."""
        try:
            logger.info("[ORCHESTRATOR] Starting Freqtrade Cognitive Strategy...")
            config = {
                "dry_run": True,
                "max_open_trades": 3,
                "stake_currency": "USDT",
                "stake_amount": 100,
                "db_url": os.getenv("DATABASE_URL", "sqlite:///./data/pythia_prod.db"),
            }
            os.environ["SQLITE_DB_PATH"] = os.getenv("SQLITE_DB_PATH", "/app/data/pythia_prod.db")
            _ = FreqtradeStrategy(config)
            logger.info("[ORCHESTRATOR] Freqtrade Strategy initialized")
        except Exception as exc:
            logger.error("[ORCHESTRATOR] Failed to initialize Freqtrade: %s", exc)

    async def start_api_server(self):
        """Launch FastAPI via uvicorn as an asyncio task."""
        logger.info("[ORCHESTRATOR] Starting FastAPI server on :8000...")
        config = uvicorn.Config(
            self.api_app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=False,
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def start_freqtrade(self):
        """Launch Freqtrade strategy in a daemon thread."""
        thread = threading.Thread(target=self._run_freqtrade_sync, daemon=True)
        thread.start()

    async def start_metrics(self):
        """Launch Prometheus exporter."""
        logger.info("[ORCHESTRATOR] Starting Prometheus Exporter on :9090...")
        try:
            self.metrics.start()
            logger.info("[ORCHESTRATOR] Prometheus metrics server started on :9090")
        except OSError as exc:
            logger.error("[ORCHESTRATOR] Failed to start metrics server: %s", exc)

    async def start_streamlit(self):
        """Launch Streamlit UI as a subprocess."""
        logger.info("[ORCHESTRATOR] Starting Streamlit Dashboard on :8501...")
        cmd = [
            "streamlit", "run",
            "backend/src/pythia/adapters/streamlit_app.py",
            "--server.address", "0.0.0.0",
            "--server.port", "8501",
            "--browser.gatherUsageStats", "false",
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self.processes.append(proc)

            while not self.should_exit:
                if proc.stdout:
                    line = proc.stdout.readline()
                    if line:
                        logger.info("[STREAMLIT] %s", line.strip())

                if proc.poll() is not None:
                    logger.error("[ORCHESTRATOR] Streamlit process terminated unexpectedly")
                    break
                await asyncio.sleep(0.1)
        except OSError as exc:
            logger.error("[ORCHESTRATOR] Failed to launch Streamlit: %s", exc)

    async def prediction_market_worker(self):
        """Background worker for prediction market arbitrage scanning."""
        logger.info("[ORCHESTRATOR] Starting Prediction Market Arbitrage Worker...")
        from pythia.adapters.pmxt_adapter import PmxtAdapter
        from pythia.application.trading.arbitrage_detector import ArbitrageDetector
        from pythia.domain.markets.prediction_market import PredictionMarket

        adapter = PmxtAdapter(
            kalshi_api_key=os.getenv("KALSHI_API_KEY"),
            kalshi_private_key_path=os.getenv("KALSHI_KEY_PATH"),
            polymarket_wallet_key=os.getenv("POLYMARKET_WALLET_KEY"),
        )
        detector = ArbitrageDetector(min_roi=0.015)

        while not self.should_exit:
            try:
                logger.debug("[ORCHESTRATOR] Scanning prediction markets...")

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
                self.metrics.record_markets_scanned("kalshi", len(kalshi_markets))

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
                    self.metrics.record_markets_scanned("polymarket", len(poly_markets))

                if poly_markets:
                    opportunities = detector.find_opportunities(kalshi_markets, poly_markets)
                    if opportunities:
                        logger.info(
                            "[ORCHESTRATOR] Found %d arbitrage opportunities",
                            len(opportunities),
                        )

                await asyncio.sleep(300)
            except Exception as exc:
                logger.error("[ORCHESTRATOR] PM Worker Error: %s", exc)
                await asyncio.sleep(30)

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

        logger.info("[ORCHESTRATOR] Pythia v4.0 — Starting all services...")
        await asyncio.gather(
            self.start_api_server(),
            self.start_metrics(),
            self.start_freqtrade(),
            self.start_streamlit(),
            self.prediction_market_worker(),
        )

    async def shutdown(self):
        """Graceful shutdown of all managed processes."""
        logger.info("[ORCHESTRATOR] Initiating graceful shutdown...")
        self.should_exit = True
        for proc in self.processes:
            logger.info("[ORCHESTRATOR] Terminating process %d", proc.pid)
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("[ORCHESTRATOR] Force-killing process %d", proc.pid)
                proc.kill()

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
