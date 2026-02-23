import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
from pythia.application.market_data import MarketDataService

@pytest.fixture
def market_data_service():
    return MarketDataService()

def test_get_quote_success(market_data_service):
    with patch('yfinance.Ticker') as mock_ticker:
        mock_ticker.return_value.fast_info.last_price = 150.0
        mock_ticker.return_value.fast_info.previous_close = 145.0
        result = market_data_service.get_quote('AAPL')
        assert result['symbol'] == 'AAPL'
        assert result['price'] == 150.0
        assert result['change'] == 5.0
        assert result['change_percent'] > 0
        assert 'timestamp' in result

def test_get_quote_fallback_to_history(market_data_service):
    with patch('yfinance.Ticker') as mock_ticker:
        mock_ticker.return_value.fast_info.last_price = None
        mock_history = pd.DataFrame({'Close': [150.0]})
        mock_ticker.return_value.history.return_value = mock_history
        result = market_data_service.get_quote('AAPL')
        assert result['price'] == 150.0

def test_get_historical_data(market_data_service):
    with patch('yfinance.Ticker') as mock_ticker:
        dates = pd.date_range(start='2023-01-01', periods=5)
        mock_data = pd.DataFrame({'Open': [100.0] * 5, 'High': [110.0] * 5, 'Low': [90.0] * 5, 'Close': [105.0] * 5, 'Volume': [1000] * 5}, index=dates)
        mock_ticker.return_value.history.return_value = mock_data
        result = market_data_service.get_historical_data('AAPL', days=5)
        assert len(result) == 5
        assert result[0]['open'] == 100.0
        assert 'date' in result[0]

def test_calculate_indicators(market_data_service):
    history = []
    for i in range(60):
        history.append({'close': 100.0 + i, 'open': 100.0, 'high': 100.0, 'low': 100.0, 'volume': 1000})
    indicators = market_data_service.calculate_indicators(history)
    assert 'sma_20' in indicators
    assert 'sma_50' in indicators
    assert 'rsi' in indicators
    assert indicators['current_price'] == 159.0
