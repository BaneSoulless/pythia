"""
Live-Fire Strategy Service
SOTA 2026

Uses pandas_ta for Technical Analysis on Real-Time Data.
Wait for buffer fill (Warm-up) before signaling.
"""
import pandas as pd
import pandas_ta as ta
import asyncio
import logging
import json
from typing import Dict, Any
from pythia.infrastructure.messaging.system_bus import SystemBus
from pythia.core.config import settings
logger = logging.getLogger(__name__)

class StrategyService:
    """
    Consumes live market data, accumulates OHLCV, calculates indicators using pandas_ta.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bus = SystemBus(config)
        self.min_history = 50
        self.buffers: Dict[str, pd.DataFrame] = {}

    async def process_tick(self, tick: Dict[str, Any]):
        """Accumulate ticks into OHLCV candles (Simplified 1-tick candle for HFT)."""
        symbol = tick['symbol']
        price = tick['last']
        ts = pd.to_datetime(tick['timestamp'], unit='ms')
        new_row = pd.DataFrame([{'close': price, 'volume': tick['volume'], 'timestamp': ts}])
        if symbol not in self.buffers:
            self.buffers[symbol] = new_row
        else:
            self.buffers[symbol] = pd.concat([self.buffers[symbol], new_row]).tail(200)
        df = self.buffers[symbol]
        if len(df) < self.min_history:
            return
        df.ta.rsi(length=14, append=True)
        df.ta.ema(length=20, append=True)
        latest = df.iloc[-1]
        signal = self._evaluate_strategy(symbol, latest)
        if signal:
            logger.info(f'STRATEGY SIGNAL: {signal}')
            await self.bus.publish_signal(signal)

    def _evaluate_strategy(self, symbol: str, data: pd.Series) -> Dict[str, Any]:
        """Simple RSI Reversal Strategy."""
        rsi = data.get('RSI_14')
        price = data['close']
        if not rsi:
            return None
        if rsi < 30:
            return {'action': 'buy', 'symbol': symbol, 'quantity': 0.001, 'price': price}
        elif rsi > 70:
            return {'action': 'sell', 'symbol': symbol, 'quantity': 0.001, 'price': price}
        return None

    async def start(self):
        """Start the service loop."""
        self.bus.connect_strategy_publisher()
        logger.info('Strategy Service: LIVE-FIRE ANALYZER ONLINE')
        data_sub = self.bus.context.socket(zmq.SUB)
        data_sub.connect(f"tcp://localhost:{self.bus.ports['data']}")
        data_sub.setsockopt_string(zmq.SUBSCRIBE, '')
        import zmq
        while True:
            try:
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f'Strategy Loop Error: {e}')
                await asyncio.sleep(1)

def run_service(config: Dict[str, Any]):
    service = StrategyService(config)
    asyncio.run(service.start())