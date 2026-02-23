import pytest
from pythia.domain.markets.prediction_market import PredictionMarket

def test_arbitrage_detection():
    kalshi = PredictionMarket(
        market_id="FED-MAR-T5.25",
        description="Fed rate hike to 5.25%",
        yes_price=0.42,
        no_price=0.58,
        platform="kalshi",
        volume=50000
    )

    polymarket = PredictionMarket(
        market_id="0x1234",
        description="Fed rate hike to 5.25%",
        yes_price=0.46,
        no_price=0.56,
        platform="polymarket",
        volume=120000
    )

    arb = kalshi.arbitrage_opportunity(polymarket)

    assert arb is not None
    assert arb["cost"] == 0.98
    assert arb["profit"] == 0.02
    assert arb["roi"] == pytest.approx(0.0204, rel=0.01)

def test_no_arbitrage_when_overpriced():
    m1 = PredictionMarket("T1", "Test", 0.60, 0.45, "kalshi", 1000)
    m2 = PredictionMarket("T2", "Test", 0.55, 0.40, "polymarket", 1000)

    assert m1.arbitrage_opportunity(m2) is None
