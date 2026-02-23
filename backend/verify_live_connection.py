"""
Live-Fire Connectivity Verification
SOTA 2026

Verifies:
1. CCXT Connection to Exchange (Testnet default)
2. API Key Authentication (HMAC-SHA256)
3. WebSocket Stream Connectivity
"""

import asyncio
import sys
import os
import logging
import ccxt.pro as ccxt

# Path Injection
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [LIVE-TEST] %(levelname)s: %(message)s')
logger = logging.getLogger("LiveVerification")

async def verify_exchange_connectivity():
    exchange_id = settings.EXCHANGE_ID
    logger.info(f"Target Exchange: {exchange_id} (Testnet: {settings.EXCHANGE_TESTNET})")
    
    if not settings.EXCHANGE_API_KEY or not settings.EXCHANGE_SECRET_KEY:
        logger.error("MISSING API KEYS in .env! Cannot verify authenticated endpoints.")
        logger.info("Please set EXCHANGE_API_KEY and EXCHANGE_SECRET_KEY in .env")
        return False

    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'apiKey': settings.EXCHANGE_API_KEY,
            'secret': settings.EXCHANGE_SECRET_KEY,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        if settings.EXCHANGE_TESTNET:
            exchange.set_sandbox_mode(True)
            
        # 1. Test Public REST (Time/Server)
        logger.info(">>> STEP 1: REST Connectivity...")
        time_sync = await exchange.fetch_time()
        logger.info(f"Exchange Time: {time_sync}")
        
        # 2. Test Authenticated REST (Balance)
        logger.info(">>> STEP 2: Authentication (Balance Check)...")
        balance = await exchange.fetch_balance()
        logger.info(f"Balance Retrieved. Total USD: {balance.get('total', {}).get('USDT', 0)}")
        
        # 3. Test WebSocket (Ticker)
        logger.info(">>> STEP 3: WebSocket Streaming...")
        symbol = 'BTC/USDT'
        ticker = await exchange.watch_ticker(symbol)
        logger.info(f"Real-Time Ticker: {symbol} Last={ticker['last']}")
        
        await exchange.close()
        return True
        
    except ccxt.AuthenticationError:
        logger.critical("AUTHENTICATION FAILED: Invalid API Keys.")
        return False
    except ccxt.NetworkError as e:
        logger.critical(f"NETWORK ERROR: {e}")
        return False
    except Exception as e:
        logger.critical(f"VERIFICATION FAILED: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_exchange_connectivity())
    if success:
        logger.info("✅ LIVE CONNECTIVITY CONFIRMED")
        sys.exit(0)
    else:
        logger.error("❌ LIVE CONNECTIVITY FAILED")
        sys.exit(1)
