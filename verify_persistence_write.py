import sys
import os
import asyncio
import logging

# Inject backend path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

# Configure Logging
logging.basicConfig(level=logging.INFO)

from architecture.execution_layer.connector import ExchangeConnector

async def test_write():
    print("🧪 TESTING DATABASE WRITE PATH...")
    
    config = {"exchange": {"name": "test"}}
    connector = ExchangeConnector(config)
    
    signal = {
        "action": "buy",
        "symbol": "KINETIC-TEST-BTC",
        "confidence": 0.99,
        "size_ratio": 0.1
    }
    
    result = await connector.execute_order(signal)
    print(f"RESULT: {result}")
    
    if result.get("status") == "filled":
        print("✅ SUCCESS: Trade executed and persisted.")
    else:
        print("❌ FAILURE: Trade not filled.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_write())
