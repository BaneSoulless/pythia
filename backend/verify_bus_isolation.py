import pytest
import asyncio
import logging
import json
import zmq.asyncio
import sys
import os

# SOTA Path Injection
# Ensure we can import 'app' from 'backend/'
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from pythia.infrastructure.messaging.system_bus import SystemBus, ConnectionState

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("TestIntegration")

@pytest.mark.asyncio
async def test_bus_rep_req_cycle():
    """
    Verifies that SystemBus can handle DATA requests correctly.
    Simulates: Service (REP) <-> Client (REQ)
    """
    # 1. Setup Service Bus (REP)
    service_config = {
        "system": {
            "ports": {"data": 5560} # Use test port
        }
    }
    service_bus = SystemBus(service_config)
    service_bus.setup_data_endpoint()
    
    assert service_bus._states['data'] == ConnectionState.CONNECTED
    
    # 2. Setup Client Socket (REQ)
    ctx = zmq.asyncio.Context()
    client_socket = ctx.socket(zmq.REQ)
    client_socket.connect("tcp://127.0.0.1:5560")
    
    # 3. Async Task for Service Loop
    async def service_loop():
        logger.info("Service Loop Started")
        try:
            # Wait for request (timeout 2s)
            req = await service_bus.handle_data_request()
            return req
        except Exception as e:
            logger.error(f"Service Error: {e}")
            return None

    # 4. Async Task for Client
    async def client_task():
        logger.info("Client Sending Request")
        await client_socket.send_json({"test": "ping"})
        reply = await client_socket.recv_json()
        return reply

    # 5. Run Concurrent
    server_task = asyncio.create_task(service_loop())
    client_task = asyncio.create_task(client_task())
    
    # Wait
    results = await asyncio.gather(server_task, client_task)
    
    received_req = results[0]
    received_reply = results[1]
    
    # 6. Verify
    assert received_req == {"test": "ping"}
    assert received_reply == {"status": "ack"}
    
    # Cleanup
    service_bus.data_socket.close()
    client_socket.close()
    ctx.term()
    print("TEST PASSED: SystemBus REP/REQ Cycle Verified")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_bus_rep_req_cycle())
