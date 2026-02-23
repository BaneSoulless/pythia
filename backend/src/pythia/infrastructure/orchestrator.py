import asyncio
import logging
import subprocess
import os
import signal
import sys
import threading
from pythia.infrastructure.monitoring.prometheus_exporter import get_metrics_exporter
from pythia.infrastructure.secrets.secrets_manager import SecretsManager
from pythia.adapters.freqtrade_adapter import FreqtradeStrategy

# Configure Logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PYTHIA-ORCHESTRATOR")

class PythiaSupervisor:
    def __init__(self):
        self.processes = []
        self.should_exit = False
        self.loop = None
        self.secrets = SecretsManager()
        self.metrics = get_metrics_exporter()

    def _load_secrets(self):
        """Loads encrypted secrets into environment variables."""
        try:
            self.secrets.load_encrypted_env()
            logger.info("[ORCHESTRATOR] 🛡️ Secrets loaded from encrypted environment.")
        except FileNotFoundError:
            logger.warning("[ORCHESTRATOR] ⚠️ No encrypted env found, falling back to plaintext.")

    def _run_freqtrade_sync(self):
        """Helper to run Freqtrade in a thread since it's blocking."""
        try:
            logger.info("[ORCHESTRATOR] Starting Freqtrade Cognitive Strategy...")
            config = {
                "dry_run": True,
                "max_open_trades": 3,
                "stake_currency": "USDT",
                "stake_amount": 100,
                "db_url": os.getenv("DATABASE_URL", "sqlite:///./data/pythia_prod.db")
            }
            # Force environment variable for domain stores
            os.environ["SQLITE_DB_PATH"] = os.getenv("SQLITE_DB_PATH", "/app/data/pythia_prod.db")
            _ = FreqtradeStrategy(config)
            logger.info("[ORCHESTRATOR] Freqtrade Strategy initialized successfully.")
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Failed to initialize Freqtrade: {e}")

    async def start_freqtrade(self):
        """Launches the Freqtrade strategy logic."""
        thread = threading.Thread(target=self._run_freqtrade_sync, daemon=True)
        thread.start()

    async def start_metrics(self):
        """Launches the Prometheus Exporter."""
        logger.info("[ORCHESTRATOR] Starting Prometheus Exporter on port 9090...")
        try:
            self.metrics.start()
            logger.info("[ORCHESTRATOR] Prometheus metrics server started on port 9090")
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Failed to start metrics server: {e}")

    async def start_streamlit(self):
        """Launches the Streamlit UI as a subprocess."""
        logger.info("[ORCHESTRATOR] Starting Streamlit Dashboard...")
        cmd = [
            "streamlit", "run", 
            "backend/src/pythia/adapters/streamlit_app.py", 
            "--server.address", "0.0.0.0",
            "--server.port", "8501",
            "--browser.gatherUsageStats", "false"
        ]
        
        try:
            proc = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True,
                bufsize=1
            )
            self.processes.append(proc)
            
            while not self.should_exit:
                if proc.stdout:
                    line = proc.stdout.readline()
                    if line:
                        logger.info(f"[STREAMLIT] {line.strip()}")
                
                if proc.poll() is not None:
                    logger.error("[ORCHESTRATOR] Streamlit process terminated unexpectedly!")
                    break
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Failed to launch Streamlit: {e}")

    async def prediction_market_worker(self):
        """Background worker for prediction market arbitrage scanning."""
        logger.info("[ORCHESTRATOR] Starting Prediction Market Arbitrage Worker...")
        from pythia.adapters.pmxt_adapter import PmxtAdapter
        from pythia.application.trading.arbitrage_detector import ArbitrageDetector
        from pythia.domain.markets.prediction_market import PredictionMarket
        
        adapter = PmxtAdapter(
            kalshi_api_key=os.getenv("KALSHI_API_KEY"),
            kalshi_private_key_path=os.getenv("KALSHI_KEY_PATH"),
            polymarket_wallet_key=os.getenv("POLYMARKET_WALLET_KEY")
        )
        detector = ArbitrageDetector(min_roi=0.015)
        
        while not self.should_exit:
            try:
                logger.debug("[ORCHESTRATOR] Scanning prediction markets for arbitrage...")
                
                # Fetch markets
                kalshi_raw = adapter.fetch_markets("kalshi", limit=50)
                kalshi_markets = [
                    PredictionMarket(
                        market_id=m["market_id"],
                        description=m["description"],
                        yes_price=m["yes_price"],
                        no_price=m["no_price"],
                        platform="kalshi",
                        volume=m.get("volume", 0)
                    ) for m in kalshi_raw
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
                            volume=m.get("volume", 0)
                        ) for m in poly_raw
                    ]
                    self.metrics.record_markets_scanned("polymarket", len(poly_markets))

                if poly_markets:
                    opportunities = detector.find_opportunities(kalshi_markets, poly_markets)
                    if opportunities:
                        logger.info(f"[ORCHESTRATOR] 🎯 Found {len(opportunities)} prediction market arbitrage ops!")

                await asyncio.sleep(300) # Scan every 5 minutes
            except Exception as e:
                logger.error(f"[ORCHESTRATOR] PM Worker Error: {e}")
                await asyncio.sleep(30)

    async def run(self):
        self._load_secrets()
        self.loop = asyncio.get_running_loop()
        
        for s in (signal.SIGINT, signal.SIGTERM):
            self.loop.add_signal_handler(s, lambda: asyncio.create_task(self.shutdown()))

        await asyncio.gather(
            self.start_metrics(),
            self.start_freqtrade(),
            self.start_streamlit(),
            self.prediction_market_worker()
        )

    async def shutdown(self):
        logger.info("[ORCHESTRATOR] Initiating graceful shutdown...")
        self.should_exit = True
        for proc in self.processes:
            logger.info(f"[ORCHESTRATOR] Terminating process {proc.pid}")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"[ORCHESTRATOR] Force-killing process {proc.pid}")
                proc.kill()
        
        logger.info("[ORCHESTRATOR] Pythia services stopped. Exiting.")
        sys.exit(0)

if __name__ == "__main__":
    supervisor = PythiaSupervisor()
    try:
        asyncio.run(supervisor.run())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.critical(f"[ORCHESTRATOR] Operational Failure: {e}")
        sys.exit(1)
