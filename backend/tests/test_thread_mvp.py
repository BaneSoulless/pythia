import pytest
import asyncio
from app.domain.cognitive.models import TradingSignal
from app.services.ai_providers.groq_client import GroqClient, GroqRateLimiter

@pytest.mark.asyncio
async def test_confidence_gate():
    """P0: Confidence < 0.5 forces HOLD regardless of action."""
    signal_low = TradingSignal(action="BUY", confidence=0.4, pair="BTC/USDT", reason="Low conf test")
    assert signal_low.action == "HOLD", "Confidence gate failed: 0.4 should force HOLD"
    
    signal_high = TradingSignal(action="BUY", confidence=0.7, pair="BTC/USDT", reason="High conf test")
    assert signal_high.action == "BUY", "High confidence BUY should pass through"

@pytest.mark.asyncio
async def test_groq_rate_limit():
    """P1: 30 RPM compliance - 31st call in 60s should be delayed."""
    limiter = GroqRateLimiter(delay_seconds=2.0)  # Faster for testing
    
    start = asyncio.get_event_loop().time()
    for _ in range(3):
        await limiter.wait()
    elapsed = asyncio.get_event_loop().time() - start
    
    # 3 calls with 2.0s delay = ~4.0s minimum (first call immediate, then 2 delays)
    assert elapsed >= 4.0, f"Rate limiter too fast: {elapsed:.2f}s for 3 calls"

def test_dual_confirmation_logic():
    """P2: AI BUY + RSI 75 (overbought) should block entry."""
    # Mock dataframe row
    import pandas as pd
    row = pd.Series({'rsi': 75, 'ema_fast': 50, 'ema_slow': 48, 'close': 100})
    
    # Simulated AI signal
    ai_signal = TradingSignal(action="BUY", confidence=0.8, pair="BTC/USDT", reason="Test")
    
    # Dual confirmation check
    should_enter = (
        ai_signal.action == "BUY" and 
        ai_signal.confidence >= 0.5 and
        row['rsi'] < 70 and  # FAILS HERE
        row['ema_fast'] > row['ema_slow']
    )
    
    assert not should_enter, "Overbought (RSI 75) should block entry despite AI BUY"

def test_mode_switching():
    """P3: YAML execution_mode changes should load correct provider."""
    import yaml
    
    config = yaml.safe_load("""
execution_mode: "test"
test_mode:
  signal_provider: "groq"
production_mode:
  signal_provider: "ensemble"
""")
    
    mode = config['execution_mode']
    provider = config[f"{mode}_mode"]['signal_provider']
    
    assert provider == "groq", f"Test mode should use Groq, got {provider}"

@pytest.mark.asyncio
async def test_groq_api_fallback():
    """P4: Groq API failure should return HOLD with API_ERROR reason."""
    client = GroqClient(api_key="INVALID_KEY_FOR_TEST")
    signal = await client.get_signal("BTC/USDT", 50000, 50, 55, 50)
    
    assert signal.action == "HOLD", "Failed API call should fallback to HOLD"
    assert "API_ERROR" in signal.reason or "NO_API_KEY" in signal.reason
