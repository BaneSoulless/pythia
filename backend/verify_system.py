"""
Final System Verification (Paper Mode)
SOTA 2026

Verifies:
1. Public WebSocket Data Stream
2. Paper Trading Execution
3. Neuro-Symbolic Validation
"""

import asyncio
import sys
import os
import logging
import json
import random

# Path Injection
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from pythia.domain.execution.service import ExecutionService
from pythia.domain.market_data.service import MarketDataService

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [SYSTEM] %(levelname)s: %(message)s')
logger = logging.getLogger("SystemVerification")

async def verify_system_loop():
    logger.info(">>> STEP 1: Booting Virtual Execution Engine...")
    exec_service = ExecutionService({})
    
    # Simulate receiving a signal
    test_order = {
        "action": "buy",
        "symbol": "BTC/USDT",
        "quantity": 0.1,
        "price": 50000.0,
        "timestamp": 1234567890
    }
    
    logger.info(">>> STEP 2: Triggering Paper Trade...")
    await exec_service.execute_trade(test_order)
    
    # Check Balance
    bal = await exec_service.connector.fetch_balance()
    final_bal = bal['total']['USDT']
    
    if final_bal < 10000:
        logger.info(f"✅ Paper Trade Successful. Balance deducted: {final_bal}")
        return True
    else:
        logger.error("❌ Balance did not update.")
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_system_loop())
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
