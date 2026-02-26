"""
Test Suite for Adapters (Alpaca, PMXT)
Applies Neuro-Symbolic workflow: translate constraints to automated assertions.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pythia.adapters.alpaca_adapter import AlpacaAdapter, AlpacaAdapterError
from pythia.adapters.pmxt_adapter import PmxtAdapter, PmxtAdapterError

@pytest.fixture
def alpaca_mock():
    with patch("pythia.adapters.alpaca_adapter.TradingClient") as MockClient:
        yield MockClient

def test_alpaca_initialization_assertions(alpaca_mock):
    """Test Pre-condition: cannot initialize Alpaca without keys."""
    with pytest.raises(AssertionError):
        AlpacaAdapter(api_key="", secret_key="")

@pytest.mark.asyncio
async def test_alpaca_pdt_compliance_rule():
    """Test Neuro-Symbolic logic: PDT rule rejection."""
    adapter = AlpacaAdapter("test", "test")
    # Rule: Equity < 25000 and daytrades >= 3 triggers violation
    status = {"equity": 24000.0, "daytrade_count": 3}
    assert adapter._check_pdt_compliance(status) is False
    
    # Safe
    status_safe = {"equity": 26000.0, "daytrade_count": 3}
    assert adapter._check_pdt_compliance(status_safe) is True

@pytest.mark.asyncio
async def test_alpaca_place_order_market_closed(alpaca_mock):
    """Test Edge Case: Market Closed Rejection."""
    adapter = AlpacaAdapter("test", "test")
    adapter.is_market_open = AsyncMock(return_value=False)
    
    with pytest.raises(AlpacaAdapterError, match="US Markets closed"):
        await adapter.place_order("AAPL", "BUY", 1.0)

@pytest.mark.asyncio
async def test_pmxt_initialization():
    """Test PmxtAdapter conditionally activates clients."""
    with patch("pythia.adapters.pmxt_adapter.pmxt.Polymarket") as PolyMock:
        adapter = PmxtAdapter(polymarket_wallet_key="pkey")
        assert adapter.poly_client is not None
        assert adapter.kalshi_client is None

@pytest.mark.asyncio
async def test_pmxt_fetch_markets_validations():
    """Test PmxtAdapter assertions on fetch."""
    adapter = PmxtAdapter(polymarket_wallet_key="pkey")
    with patch("pythia.adapters.pmxt_adapter.pmxt.Polymarket"):
        with pytest.raises(AssertionError):
            await adapter.fetch_markets(limit=-5, platform="polymarket")

@pytest.mark.asyncio
async def test_pmxt_place_order_missing_price():
    """Test Edge Case: PM requires explicit limit price."""
    adapter = PmxtAdapter(polymarket_wallet_key="pkey")
    with pytest.raises(AssertionError, match="explicit limit pricing"):
        await adapter.place_order("MARKET_ID", "BUY", 10.0, price=None, platform="polymarket")
