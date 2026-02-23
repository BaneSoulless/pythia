"""
Modular Core - Data Layer
Sensory Fidelity: Live Market Stream (Binance)
"""
import asyncio
import json
import logging
import time
from collections import deque
from typing import Callable, Coroutine, Optional, Dict, Any

# Try importing websockets, if failing fallback to log
try:
    import websockets
except ImportError:
    websockets = None

logger = logging.getLogger("DataFeed")

class DataPipeline:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.symbol = "btcusdt" # Internal default
        self.buffer = deque(maxlen=1000)
        self.running = False
        self._subscribers = []

    def subscribe(self, callback: Callable[[Dict], Coroutine[Any, Any, None]]):
        """Register a subscriber callback."""
        self._subscribers.append(callback)

    async def start_stream(self):
        """
        Connect to Binance WebSocket and stream live candles.
        Deprecates synthetic RNG.
        """
        if not websockets:
            logger.critical("websockets library missing. Sensory fidelity compromised.")
            return

        self.running = True
        # Using 1m kline for high fidelity
        uri = f"wss://stream.binance.com:9443/ws/{self.symbol}@kline_1m"
        logger.info(f"Connecting to Sensory Stream: {uri}")
        
        while self.running:
            try:
                async with websockets.connect(uri) as websocket:
                    logger.info("Sensory Stream ESTABLISHED.")
                    
                    while self.running:
                        msg = await websocket.recv()
                        data = json.loads(msg)
                        
                        # Process only kline events
                        if 'e' in data and data['e'] == 'kline':
                            candle = self._parse_binance_kline(data)
                            self.buffer.append(candle)
                            
                            # Notify subscribers
                            for sub in self._subscribers:
                                try:
                                    await sub(candle)
                                except Exception as e:
                                    logger.error(f"Subscriber error: {e}")
                                    
            except Exception as e:
                logger.error(f"Sensory Stream INTERRUPTED: {e}. Retrying in 5s...")
                await asyncio.sleep(5)

    def _parse_binance_kline(self, data: Dict) -> Dict:
        """Normalize Binance format to internal schema."""
        k = data['k']
        return {
            "symbol": data['s'],
            "timestamp": data['E'],
            "open": float(k['o']),
            "high": float(k['h']),
            "low": float(k['l']),
            "close": float(k['c']),
            "volume": float(k['v']),
            "closed": k['x'], # True if candle is closed
            "source": "live_binance"
        }

    # Legacy method compatibility (optional, but good for transition)
    def process_tick(self, tick):
        self.buffer.append(tick)
