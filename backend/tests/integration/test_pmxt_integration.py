"""Integration tests for PmxtAdapter and ArbitrageDetector.

Validates prediction market adapter initialization, market fetching,
order placement, and cross-platform arbitrage detection logic.
"""
import pytest
from unittest.mock import patch, MagicMock
from pythia.adapters.pmxt_adapter import PmxtAdapter
from pythia.application.trading.arbitrage_detector import ArbitrageDetector
from pythia.domain.markets.prediction_market import PredictionMarket


class TestPmxtAdapterInitialization:
    """Verify adapter initializes correctly with and without credentials."""

    def test_init_no_credentials(self):
        adapter = PmxtAdapter()
        assert adapter.poly_client is None
        assert adapter.kalshi_client is None

    @patch("pythia.adapters.pmxt_adapter.pmxt")
    def test_init_polymarket_only(self, mock_pmxt):
        mock_pmxt.Polymarket.return_value = MagicMock()
        adapter = PmxtAdapter(polymarket_wallet_key="test_key")
        assert adapter.poly_client is not None
        assert adapter.kalshi_client is None

    @patch("pythia.adapters.pmxt_adapter.pmxt")
    def test_init_kalshi_only(self, mock_pmxt):
        mock_pmxt.Kalshi.return_value = MagicMock()
        adapter = PmxtAdapter(
            kalshi_api_key="test_api_key",
            kalshi_private_key_path="/tmp/test_key.pem",
        )
        assert adapter.kalshi_client is not None
        assert adapter.poly_client is None

    @patch("pythia.adapters.pmxt_adapter.pmxt")
    def test_init_both_platforms(self, mock_pmxt):
        mock_pmxt.Polymarket.return_value = MagicMock()
        mock_pmxt.Kalshi.return_value = MagicMock()
        adapter = PmxtAdapter(
            polymarket_wallet_key="poly_key",
            kalshi_api_key="kalshi_key",
            kalshi_private_key_path="/tmp/key.pem",
        )
        assert adapter.poly_client is not None
        assert adapter.kalshi_client is not None


class TestPmxtAdapterFetchMarkets:
    """Verify market fetching returns expected structure."""

    @patch("pythia.adapters.pmxt_adapter.pmxt")
    def test_fetch_kalshi_markets(self, mock_pmxt):
        mock_client = MagicMock()
        mock_client.fetch_markets.return_value = [
            {
                "market_id": "FED-RATE-MAR",
                "description": "Fed Rate Hike March 2026",
                "yes_price": 0.42,
                "no_price": 0.58,
                "volume": 150000,
            }
        ]
        mock_pmxt.Kalshi.return_value = mock_client

        adapter = PmxtAdapter(
            kalshi_api_key="key",
            kalshi_private_key_path="/tmp/k.pem",
        )
        markets = adapter.fetch_markets("kalshi", limit=10)

        assert len(markets) == 1
        assert markets[0]["market_id"] == "FED-RATE-MAR"
        mock_client.fetch_markets.assert_called_once_with(limit=10)

    def test_fetch_unsupported_platform_raises(self):
        adapter = PmxtAdapter()
        with pytest.raises(ValueError, match="Unsupported platform"):
            adapter.fetch_markets("binance")


class TestPmxtAdapterPlaceOrder:
    """Verify order placement logic."""

    @patch("pythia.adapters.pmxt_adapter.pmxt")
    def test_place_order_kalshi(self, mock_pmxt):
        mock_client = MagicMock()
        mock_client.place_order.return_value = {"order_id": "ORD-001", "status": "filled"}
        mock_pmxt.Kalshi.return_value = mock_client

        adapter = PmxtAdapter(
            kalshi_api_key="key",
            kalshi_private_key_path="/tmp/k.pem",
        )
        result = adapter.place_order("kalshi", "FED-RATE", "buy", 100.0, 0.42)

        assert result["order_id"] == "ORD-001"
        mock_client.place_order.assert_called_once_with(
            market_id="FED-RATE", side="buy", amount=100.0, price=0.42
        )


class TestArbitrageDetector:
    """Verify cross-platform arbitrage detection."""

    def _make_market(
        self, market_id: str, desc: str, yes: float, no: float, platform: str
    ) -> PredictionMarket:
        return PredictionMarket(
            market_id=market_id,
            description=desc,
            yes_price=yes,
            no_price=no,
            platform=platform,
            volume=10000,
        )

    def test_finds_arbitrage_when_total_cost_below_one(self):
        detector = ArbitrageDetector(min_roi=0.01)
        kalshi = [
            self._make_market("K1", "Fed Rate Hike March", 0.42, 0.58, "kalshi")
        ]
        poly = [
            self._make_market("P1", "Fed Rate Hike March", 0.45, 0.53, "polymarket")
        ]
        # total_cost = 0.42 (kalshi YES) + 0.53 (poly NO) = 0.95
        # profit = 0.05, roi = 0.05/0.95 ≈ 5.26%
        opps = detector.find_opportunities(kalshi, poly)
        assert len(opps) == 1
        assert opps[0]["roi"] > 0.01

    def test_no_arbitrage_when_total_cost_above_one(self):
        detector = ArbitrageDetector(min_roi=0.01)
        kalshi = [
            self._make_market("K1", "Bitcoin 100K June", 0.60, 0.40, "kalshi")
        ]
        poly = [
            self._make_market("P1", "Bitcoin 100K June", 0.55, 0.45, "polymarket")
        ]
        # total_cost = 0.60 + 0.45 = 1.05 → no arb
        opps = detector.find_opportunities(kalshi, poly)
        assert len(opps) == 0

    def test_market_matching_by_description(self):
        detector = ArbitrageDetector(min_roi=0.01)
        kalshi = [
            self._make_market("K1", "Fed Rate Hike March 2026", 0.42, 0.58, "kalshi")
        ]
        poly = [
            self._make_market("P1", "Completely different event", 0.55, 0.40, "polymarket")
        ]
        opps = detector.find_opportunities(kalshi, poly)
        assert len(opps) == 0

    def test_min_roi_filter(self):
        detector = ArbitrageDetector(min_roi=0.10)
        kalshi = [
            self._make_market("K1", "Fed Rate Hike March", 0.48, 0.52, "kalshi")
        ]
        poly = [
            self._make_market("P1", "Fed Rate Hike March", 0.50, 0.50, "polymarket")
        ]
        # total_cost = 0.48 + 0.50 = 0.98
        # profit = 0.02, roi = 0.02/0.98 ≈ 2.04% < 10% threshold
        opps = detector.find_opportunities(kalshi, poly)
        assert len(opps) == 0


class TestPredictionMarketDomainEntity:
    """Verify domain entity logic."""

    def test_implied_probability(self):
        market = PredictionMarket(
            market_id="M1",
            description="Test",
            yes_price=0.65,
            no_price=0.35,
            platform="kalshi",
            volume=1000,
        )
        assert market.implied_probability() == 0.65

    def test_arbitrage_opportunity_exists(self):
        market_a = PredictionMarket(
            market_id="A", description="Test", yes_price=0.40,
            no_price=0.60, platform="kalshi", volume=1000,
        )
        market_b = PredictionMarket(
            market_id="B", description="Test", yes_price=0.45,
            no_price=0.50, platform="polymarket", volume=1000,
        )
        result = market_a.arbitrage_opportunity(market_b)
        assert result is not None
        assert result["cost"] == pytest.approx(0.90)
        assert result["profit"] == pytest.approx(0.10)

    def test_no_arbitrage_opportunity(self):
        market_a = PredictionMarket(
            market_id="A", description="Test", yes_price=0.60,
            no_price=0.40, platform="kalshi", volume=1000,
        )
        market_b = PredictionMarket(
            market_id="B", description="Test", yes_price=0.55,
            no_price=0.45, platform="polymarket", volume=1000,
        )
        result = market_a.arbitrage_opportunity(market_b)
        assert result is None
