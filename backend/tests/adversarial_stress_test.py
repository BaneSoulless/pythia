import asyncio
import time
import logging
import sys
import os
import json
from zmq.asyncio import Context
import zmq

# SOTA Path Injection
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, root_dir)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] STRESS: %(message)s')
logger = logging.getLogger("StressTest")

async def stress_test_bus():
    """
    Simulates a 'Red Team' DDoS attack on the internal bus 
    to verify stability and throughput.
    """
    ctx = Context()
    
    # 1. Connect as a Strategy Subscriber (Listening to Execution Pub)
    # Note: Execution Pub binds to 5555. We sub to localhost:5555.
    sub_socket = ctx.socket(zmq.SUB)
    sub_socket.connect("tcp://localhost:5555")
    sub_socket.subscribe("")
    
    # 2. Connect as an Execution Publisher (Simulating the Execution Service)
    # Wait, the Execution Service BINDS. So we should actually simulate the STRATEGY service
    # connecting to the Execution Service.
    # Actually, let's test the 'Data' endpoint (REP/REQ) for latency.
    
    # Data Layer binds REP on 5557. We will be a REQ client.
    req_socket = ctx.socket(zmq.REQ)
    req_socket.connect("tcp://127.0.0.1:5557")
    
    logger.info("Starting Stress Test on Data Endpoint (Port 5557)...")
    
    failures = 0
    successes = 0
    start_time = time.time()
    
    # ATTACK VECTOR: 1000 requests in rapid succession
    for i in range(100):
        try:
            payload = json.dumps({"action": "ping", "id": i})
            
            # Send with 1s timeout
            await req_socket.send_string(payload)
            
            # Receive with 1s timeout
            if await req_socket.poll(1000):
                reply = await req_socket.recv_string()
                successes += 1
            else:
                logger.error(f"Timeout on request {i}")
                # Reset socket on timeout in ZMQ REQ/REP pattern is complex, 
                # often easier to recreate. marking as fail.
                failures += 1
                
        except Exception as e:
            logger.error(f"Error on request {i}: {e}")
            failures += 1
            
    duration = time.time() - start_time
    logger.info(f"Test Complete in {duration:.2f}s")
    logger.info(f"Success: {successes}, Failures: {failures}")
    logger.info(f"Throughput: {successes/duration:.1f} req/s")
    
    ctx.term()

if __name__ == "__main__":
    # We need the system running for this to work.
    # This script assumes scheduler_main.py is ALREADY RUNNING.
    asyncio.run(stress_test_bus())
