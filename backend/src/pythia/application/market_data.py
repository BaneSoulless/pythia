import logging
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
logger = logging.getLogger(__name__)

class MarketDataService:
    """
    Service for retrieving market data from external sources (Yahoo Finance)
    """

    def __init__(self):
        self.cache = {}
        self.cache_expiry = 60

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get current price quote for a symbol
        """
        try:
            cache_key = f'quote_{symbol}'
            if cache_key in self.cache:
                timestamp, data = self.cache[cache_key]
                if (datetime.now() - timestamp).total_seconds() < self.cache_expiry:
                    return data
            ticker = yf.Ticker(symbol)
            price = ticker.fast_info.last_price
            prev_close = ticker.fast_info.previous_close
            if price is None:
                history = ticker.history(period='1d')
                if history.empty:
                    raise ValueError(f'No data available for {symbol}')
                price = history['Close'].iloc[-1]
                prev_close = price
            change = price - prev_close
            change_percent = change / prev_close * 100 if prev_close else 0
            result = {'symbol': symbol, 'price': float(price), 'change': float(change), 'change_percent': float(change_percent), 'volume': 0, 'timestamp': datetime.now().isoformat()}
            self.cache[cache_key] = (datetime.now(), result)
            logger.info(f'Fetched quote for {symbol}: ')
            return result
        except Exception as e:
            logger.error(f'Error fetching quote for {symbol}: {e}')
            return {'symbol': symbol, 'price': 0.0, 'change': 0.0, 'change_percent': 0.0, 'volume': 0, 'error': str(e)}

    def get_historical_data(self, symbol: str, days: int=30) -> List[Dict]:
        """
        Get historical price data

        Args:
            symbol: Stock symbol
            days: Number of days of history

        Returns:
            List of daily OHLCV data
        """
        try:
            ticker = yf.Ticker(symbol)
            history = ticker.history(period=f'{days + 5}d')
            history = history.tail(days)
            data = []
            for date, row in history.iterrows():
                data.append({'date': date.strftime('%Y-%m-%d'), 'open': float(row['Open']), 'high': float(row['High']), 'low': float(row['Low']), 'close': float(row['Close']), 'volume': int(row['Volume']) if 'Volume' in history.columns else 0})
            logger.info(f'Fetched {len(data)} days of history for {symbol}')
            return data
        except Exception as e:
            logger.error(f'Error fetching historical data for {symbol}: {e}')
            return []

    def calculate_indicators(self, history: List[Dict]) -> Dict:
        """
        Calculate technical indicators from historical data

        Args:
            history: List of OHLCV dicts

        Returns:
            Dict of calculated indicators
        """
        if len(history) < 20:
            return {}
        closes = [d['close'] for d in history]
        sma_20 = sum(closes[-20:]) / 20
        sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None

        def calculate_rsi(prices, period=14):
            if len(prices) < period + 1:
                return 50.0
            gains = []
            losses = []
            for i in range(1, len(prices)):
                change = prices[i] - prices[i - 1]
                gains.append(max(change, 0))
                losses.append(abs(min(change, 0)))
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            if avg_loss == 0:
                return 100.0
            rs = avg_gain / avg_loss
            rsi = 100 - 100 / (1 + rs)
            return rsi
        rsi = calculate_rsi(closes)
        return {'sma_20': sma_20, 'sma_50': sma_50, 'rsi': rsi, 'current_price': closes[-1]}

    def calculate_sma(self, prices: List[float], period: int) -> float:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return 0.0
        return sum(prices[-period:]) / period

    def calculate_rsi(self, prices: List[float], period: int=14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0
        gains = []
        losses = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            gains.append(max(change, 0))
            losses.append(abs(min(change, 0)))
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - 100 / (1 + rs)
market_data_service = MarketDataService()