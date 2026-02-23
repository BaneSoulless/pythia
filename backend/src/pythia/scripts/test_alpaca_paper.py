import asyncio
import logging
import os
from pythia.adapters.alpaca_adapter import AlpacaAdapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ALPACA-PAPER-TEST")

async def run_test():
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    
    if not api_key or not secret_key:
        logger.error("Missing ALPACA credentials in environment.")
        return

    adapter = AlpacaAdapter(api_key, secret_key, paper=True)
    
    try:
        logger.info("Checking account status...")
        status = await adapter.get_account_status()
        logger.info(f"Account Status: {status}")
        
        logger.info("Checking market hours...")
        is_open = adapter.is_market_open()
        logger.info(f"Market Open: {is_open}")
        
        # Test order (only if market is open or using specific paper settings)
        # Note: In a real test script for paper trading, we might use AAPL or SPY
        try:
            logger.info("Attempting small paper buy for SPY...")
            order = await adapter.place_order("SPY", 1, "BUY")
            logger.info(f"Order Successful: {order}")
        except Exception as e:
            logger.warning(f"Order skipped or failed (likely closed market or PDT): {e}")

    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
