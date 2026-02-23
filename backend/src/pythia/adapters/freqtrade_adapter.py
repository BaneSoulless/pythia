import asyncio
import logging
import threading
from typing import Dict, Any, Optional
import pandas as pd
from freqtrade.strategy import IStrategy
try:
    from pythia.domain.cognitive.models import TradingSignal
except ImportError:
    from dataclasses import dataclass

    @dataclass
    class TradingSignal:
        action: str
        confidence: float
        pair: str
        reason: str
        stop_loss_pct: float = 0.02

        @classmethod
        def validation_fail_mock(cls):
            return cls(action='HOLD', confidence=0.0, pair='', reason='MOCK')
try:
    from pythia.application.ai_providers.groq_client import GroqClient
except ImportError:

    class GroqClient:

        async def get_signal(self, *args, **kwargs) -> TradingSignal:
            return TradingSignal(action='HOLD', confidence=0.0, pair='test', reason='Mocked Provider')
logger = logging.getLogger(__name__)

class FreqtradeStrategy(IStrategy):
    """
    Adapter per eseguire logica MVP Freqtrade incapsulata in Core Enterprise PYTHIA.
    MoE (Mixture of Experts) implementation: Technical Indicators + Semantic AI.
    """
    INTERFACE_VERSION = 3
    minimal_roi = {'0': 0.05, '30': 0.02, '60': 0.01}
    stoploss = -0.05
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    process_only_new_candles = True
    use_exit_signal = True
    can_short = False

    def __init__(self, config: dict):
        super().__init__(config)
        self.groq_client = GroqClient()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

    def _run_event_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def get_ai_signal(self, pair: str, price: float, rsi: float, ema_fast: float, ema_slow: float) -> TradingSignal:
        """Call async provider in a synchronous Thread context for Freqtrade DataFrame map."""
        future = asyncio.run_coroutine_threadsafe(self.groq_client.get_signal(pair, price, rsi, ema_fast, ema_slow), self._loop)
        try:
            signal = future.result(timeout=5.0)
            logger.info(f"Groq Signal for {pair}: {signal.action} (Confidence: {signal.confidence})")
            return signal
        except Exception as e:
            logger.error(f'Timeout o errore AI signal proxy: {e}')
            return TradingSignal(action='HOLD', confidence=0.0, pair=pair, reason='TIMEOUT')

    def emit_trade_event(self, pair: str, action: str, price: float, confidence: float):
        """Emit trade event to EventBus for persistence."""
        from pythia.core.event_bus import emit, EventType
        data = {
            "pair": pair,
            "action": action,
            "price": price,
            "confidence": confidence,
            "timestamp": pd.Timestamp.now().isoformat()
        }
        asyncio.run_coroutine_threadsafe(emit(EventType.TRADE_EXECUTED, data, source="freqtrade_adapter"), self._loop)

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        import ta
        dataframe['rsi'] = ta.momentum.RSIIndicator(close=dataframe['close'], window=14).rsi()
        dataframe['ema_fast'] = ta.trend.EMAIndicator(close=dataframe['close'], window=12).ema_indicator()
        dataframe['ema_slow'] = ta.trend.EMAIndicator(close=dataframe['close'], window=26).ema_indicator()
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Dual Technical Confirmation."""
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'ai_confidence'] = 0.0
        if dataframe.empty:
            return dataframe
        for i in range(len(dataframe)):
            if pd.isna(dataframe.iloc[i]['rsi']) or pd.isna(dataframe.iloc[i]['ema_fast']):
                continue
            ai_signal = self.get_ai_signal(metadata['pair'], dataframe.iloc[i]['close'], dataframe.iloc[i]['rsi'], dataframe.iloc[i]['ema_fast'], dataframe.iloc[i]['ema_slow'])
            dataframe.at[i, 'ai_confidence'] = ai_signal.confidence
            if ai_signal.action == 'BUY' and ai_signal.confidence >= 0.5:
                if dataframe.iloc[i]['rsi'] < 70 and dataframe.iloc[i]['ema_fast'] > dataframe.iloc[i]['ema_slow']:
                    dataframe.at[i, 'enter_long'] = 1
                    self.emit_trade_event(metadata['pair'], "BUY", dataframe.iloc[i]['close'], ai_signal.confidence)
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Exit constraints (AI generated SELLs overrule hard TPs logic)."""
        dataframe.loc[:, 'exit_long'] = 0
        if dataframe.empty:
            return dataframe
        for i in range(len(dataframe)):
            if pd.isna(dataframe.iloc[i]['rsi']):
                continue
            ai_signal = self.get_ai_signal(metadata['pair'], dataframe.iloc[i]['close'], dataframe.iloc[i]['rsi'], dataframe.iloc[i]['ema_fast'], dataframe.iloc[i]['ema_slow'])
            if ai_signal.action == 'SELL' and ai_signal.confidence >= 0.7:
                dataframe.at[i, 'exit_long'] = 1
                self.emit_trade_event(metadata['pair'], "SELL", dataframe.iloc[i]['close'], ai_signal.confidence)
        return dataframe

def start_freqtrade_bot():
    """Launch Freqtrade bot in test mode (blocking call)."""
    from freqtrade.configuration import Configuration
    from freqtrade.worker import Worker
    import sys
    import os
    config_path = 'freqtrade_config.json'
    if not os.path.exists(config_path):
        logger.error(f'Missing {config_path}. Run setup first.')
        sys.exit(1)
    args = ['trade', '--config', config_path, '--strategy', 'FreqtradeStrategy']
    config = Configuration.from_files([config_path])
    worker = Worker(args=args, config=config['original_config'])
    worker.run()