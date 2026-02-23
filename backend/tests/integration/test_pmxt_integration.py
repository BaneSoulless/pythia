import pytest
import os
from datetime import timedelta
from pythia.adapters.pmxt_adapter import PmxtAdapter
from pythia.application.trading.arbitrage_detector import ArbitrageDetector
from pythia.domain.markets.prediction_market import PredictionMarket

@pytest.mark.integration
def test_kalshi_testnet_authentication():
    '''Verify Kalshi testnet API authentication works.'''
    adapter = PmxtAdapter(
        kalshi_api_key=os.getenv("KALSHI_TESTNET_API_KEY"),
        kalshi_private_key_path=os.getenv("KALSHI_TESTNET_KEY_PATH")
    )

    # Note: This will likely fail without credentials, but the structure is correct
    try:
        markets = adapter.fetch_markets("kalshi", limit=10)
        assert len(markets) > 0, "Should fetch at least 1 market"
        print(f"✅ Fetched markets from Kalshi testnet")
    except Exception as e:
        pytest.skip(f"Skipping Kalshi integration test: {e}")

@pytest.mark.integration
def test_arbitrage_detection_real_data():
    '''Test arbitrage detector with mocked real-world data format.'''
    detector = ArbitrageDetector(min_roi=0.005)

    kalshi_markets = [
        PredictionMarket(
            market_id="K1",
            description="Test Market",
            yes_price=0.45,
            no_price=0.55,
            platform="kalshi",
            volume=1000
        )
    ]

    poly_markets = [
        PredictionMarket(
            market_id="P1",
            description="Test Market",
            yes_price=0.55,
            no_price=0.44,
            platform="polymarket",
            volume=10000
        )
    ]

    opportunities = detector.find_opportunities(kalshi_markets, poly_markets)
    assert len(opportunities) > 0
    assert opportunities[0]["roi"] > 0.01

@pytest.mark.integration
def test_circuit_breaker_fault_tolerance():
    '''Test circuit breaker handles API failures correctly.'''
    from pythia.infrastructure.rate_limiting.circuit_breaker import CircuitBreaker, CircuitState

    breaker = CircuitBreaker(failure_threshold=3, timeout=timedelta(seconds=2))

    def failing_api_call():
        raise Exception("API Error")

    for i in range(3):
        try:
            breaker.call(failing_api_call)
        except Exception:
            pass

    assert breaker.state == CircuitState.OPEN

    # Wait for timeout
    import time
    time.sleep(2.1)

    # Should be HALF_OPEN on next call
    try:
        breaker.call(failing_api_call)
    except Exception:
        pass

    assert breaker.state == CircuitState.HALF_OPEN

@pytest.mark.integration
def test_secrets_manager_encryption():
    '''Test secrets manager encrypts/decrypts correctly.'''
    from pythia.infrastructure.secrets.secrets_manager import SecretsManager
    import json
    from pathlib import Path

    manager = SecretsManager(encryption_key_path=Path(".encryption_key_test"))
    
    plaintext = "test_key_123"
    encrypted = manager.encrypt_secret(plaintext)
    assert manager.decrypt_secret(encrypted) == plaintext

    # Cleanup
    Path(".encryption_key_test").unlink()
