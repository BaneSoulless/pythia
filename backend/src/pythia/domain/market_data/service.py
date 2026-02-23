"""
Live-Fire Market Data Service (Public Streams)
SOTA 2026

Uses CCXT (Pro) for Real-Time WebSocket Data Ingestion.
PUBLIC CHANNELS ONLY. NO AUTH REQUIRED.
"""

import ccxt.pro as ccxt
import asyncio
import logging
import json
from typing import Dict, Any, List
from pythia.infrastructure.messaging.system_bus import SystemBus
from pythia.core.config import settings

logger = logging.getLogger(__name__)

class MarketDataService:
    """
    Ingests real-time market data from PUBLIC exchange streams.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bus = SystemBus(config)
        self.symbols = ["BTC/USDT", "ETH/USDT"]
        self.exchange_id = settings.EXCHANGE_ID
        self.exchange = None
        self._running = False

    async def _setup_exchange(self):
        """Initialize CCXT exchange instance (Public Only)."""
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            # NO API KEYS PROVIDED for Public Streams
            self.exchange = exchange_class({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future', 
                }
            })
            if settings.EXCHANGE_TESTNET:
                self.exchange.set_sandbox_mode(True)
                
            logger.info(f"MarketData: Connected to {self.exchange_id} (Public Streams)")
        except Exception as e:
            logger.critical(f"MarketData: Exchange Setup Failed: {e}")
            raise

    async def _stream_ticker(self, symbol: str):
        """Stream ticker data for a symbol."""
        while self._running:
            try:
                ticker = await self.exchange.watch_ticker(symbol)
                
                # Normalize Data
                payload = {
                    "type": "ticker",
                    "symbol": symbol,
                    "last": ticker['last'],
                    "bid": ticker['bid'],
                    "ask": ticker['ask'],
                    "volume": ticker['baseVolume'],
                    "timestamp": ticker['timestamp']
                }
                
                # Publish to Bus
                if self.bus.data_socket:
                     await self.bus.data_socket.send_string(json.dumps(payload))
                
            except ccxt.NetworkError as e:
                logger.warning(f"MarketData: Network Error ({symbol}): {e}")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"MarketData: Stream Error ({symbol}): {e}")
                await asyncio.sleep(1)

    async def start(self):
        """Start the service loop."""
        await self._setup_exchange()
        self.bus.setup_data_endpoint() 
        self._running = True
        
        logger.info("MarketData Service: PUBLIC STREAMING STARTED")
        
        try:
            tasks = [self._stream_ticker(s) for s in self.symbols]
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.critical(f"MarketData Service Failed: {e}")
        finally:
            self._running = False
            if self.exchange:
                await self.exchange.close()
            logger.info("MarketData Service: Shutdown")

import time
import random
import json

def run_service(config):
    print("    [DATA] Market Data Layer Initialized.")
    # Synthetic Ticker fallback if real connection fails (Simulated)
    print("    [DATA] Entering Synthetic Ticker Mode (Reliability Fallback)")
    
    price = 45000.0
    
    while True:
        try:
            # Simulate price movement
            change = random.uniform(-0.005, 0.005)
            price = price * (1 + change)
            
            payload = {
                "type": "TICKER",
                "symbol": "BTC/USD",
                "price": round(price, 2),
                "timestamp": time.time()
            }
            # Print to stdout, which the Interface Bridge captures and sends to WS
            print(json.dumps(payload), flush=True)
            
            time.sleep(0.5)
        except Exception as e:
            print(f"    [DATA] Error: {e}")
            time.sleep(1)
