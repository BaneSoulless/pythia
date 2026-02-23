"""
Client per l'API Groq con rate limiting (30 RPM, max 1 richiesta ogni 2.1 secondi).
"""
import asyncio
import json
import logging
import os
import time
from typing import Optional
from groq import AsyncGroq
from pythia.domain.cognitive.models import TradingSignal

logger = logging.getLogger(__name__)

class GroqRateLimiter:
    """Rate limiter semplice per 30 RPM (Thread MVP zero-cost)."""
    def __init__(self, delay_seconds: float = 2.1):
        self.delay_seconds = delay_seconds
        self._last_call: float = 0.0
        self._lock = asyncio.Lock()

    async def wait(self):
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_call
            if elapsed < self.delay_seconds:
                sleep_time = self.delay_seconds - elapsed
                await asyncio.sleep(sleep_time)
            self._last_call = time.time()


class GroqClient:
    """Client per Groq API che emette segnali compatibili con Pydantic TradingSignal."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.client = AsyncGroq(api_key=self.api_key) if self.api_key else None
        self.rate_limiter = GroqRateLimiter()
        
    async def get_signal(self, pair: str, price: float, rsi: float, ema_fast: float, ema_slow: float) -> TradingSignal:
        if not self.client:
            logger.warning("GROQ_API_KEY non configurata. Ritorno segnale HOLD di fallback.")
            return TradingSignal(action="HOLD", confidence=0.0, pair=pair, reason="NO_API_KEY")
            
        prompt = (
            f"Analyze {pair} market. Recent price: {price}, RSI: {rsi}, "
            f"EMA signals: (fast: {ema_fast}, slow: {ema_slow}). "
            f"Output JSON ONLY with action (BUY/SELL/HOLD), confidence (0.0-1.0) as float, reason (<280 chars), and pair '{pair}'."
        )
        
        # Phase 5: Production Hardening - Retry Logic with backoff
        max_retries = 3
        retry_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                await self.rate_limiter.wait()
                
                chat_completion = await self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are an AI trading expert. You only output valid JSON representing a TradingSignal."},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama3-8b-8192",
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                
                content = chat_completion.choices[0].message.content
                return TradingSignal.model_validate_json(content)
                
            except Exception as e:
                logger.warning(f"Tentativo {attempt + 1}/{max_retries} fallito per {pair}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt)) # Exponential backoff
                else:
                    logger.error(f"Errore generazione segnale Groq dopo {max_retries} tentativi: {e}")
                    return TradingSignal(action="HOLD", confidence=0.0, pair=pair, reason=f"API_ERROR: {str(e)[:100]}")
