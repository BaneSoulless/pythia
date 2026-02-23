import asyncio
import multiprocessing as mp
import json
import logging
import sys
import os
import time
import platform
from typing import Dict, Any

# --- CRITICAL WINDOWS FIX ---
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# ----------------------------

# CONFIGURAZIONE LOGGING
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("Orchestrator")

# PATH INJECTION (SOTA Normalization)
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, root_dir) # Add root for utils.py
sys.path.insert(0, current_dir) # Add backend/ for app imports

from utils import recursive_dependency_injector
repo_path = os.path.join(root_dir, 'temp_repos')
if os.path.exists(repo_path):
    recursive_dependency_injector(repo_path)

# IMPORT SISTEMA (Infrastructure)
from pythia.infrastructure.messaging.system_bus import SystemBus, bus_listener

def load_config() -> Dict[str, Any]:
    # Look for config in root
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
    if not os.path.exists(config_path):
         # check current dir
         if os.path.exists('config.json'):
             config_path = 'config.json'
         
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"config.json not found at {config_path}, using defaults")
        return {}

# --- PROCESSO DATI ---
def run_data_layer(bus_queue, config):
    print("DEBUG: Launching Market Data Layer...")
    try:
        from pythia.domain.market_data.service import run_service
        run_service(config)
    except Exception as e:
        print(f"CRITICAL ERROR in Data Layer: {e}")
        import traceback
        traceback.print_exc()

# --- PROCESSO COGNITIVO (AGENTI) ---
def run_cognitive_layer(bus_queue, config):
    from pythia.domain.cognitive.service import run_service
    run_service(config)

# --- PROCESSO STRATEGIA ---
def run_strategy_layer(bus_queue, config):
    from pythia.domain.strategy.service import run_service
    run_service(config)

# --- PROCESSO ESECUZIONE ---
def run_execution_layer(bus_queue, config):
    from pythia.domain.execution.service import run_service
    run_service(config)


# --- BUS PRINCIPALE ---
def start_bus(bus_queue, config):
    """Start the system bus with heartbeat monitoring."""
    import asyncio
    
    async def heartbeat_loop(bus):
        """Injects a heartbeat every 1s to keep the UI pipe open."""
        while True:
            try:
                payload = {
                    "type": "HEARTBEAT", 
                    "status": "NOMINAL", 
                    "timestamp": time.time(),
                    "msg": "SYSTEM ALIVE"
                }
                print(json.dumps(payload), flush=True)
                await asyncio.sleep(1.0)
            except Exception as e:
                print(f"Heartbeat Error: {e}")
                await asyncio.sleep(1.0)

    async def main_loop(bus):
        await asyncio.gather(
            bus_listener(bus),
            heartbeat_loop(bus)
        )

    bus = SystemBus(config)
    bus.setup_execution_endpoint()
    bus.setup_strategy_endpoint()
    bus.setup_data_endpoint()
    bus_queue.put("READY")
    
    asyncio.run(main_loop(bus))

if __name__ == "__main__":
    try:
        mp.set_start_method('spawn')
    except RuntimeError:
        pass

    logger.info("Initializing NEURAL ARCHITECT BOT (v2026 SOTA Refactor)...")
    config = load_config()
    bus_queue = mp.Queue()
    
    # Avvio Bus
    p_bus = mp.Process(target=start_bus, args=(bus_queue, config))
    p_bus.start()
    bus_queue.get() # Wait for ready
    
    # Avvio Moduli
    procs = [
        mp.Process(target=run_data_layer, args=(bus_queue, config)),
        mp.Process(target=run_strategy_layer, args=(bus_queue, config)),
        mp.Process(target=run_execution_layer, args=(bus_queue, config)),
        mp.Process(target=run_cognitive_layer, args=(bus_queue, config))
    ]
    
    for p in procs: p.start()
    
    logger.info("SYSTEM FULLY OPERATIONAL. Monitoring Agents (SOTA Architecture)...")
    
    try:
        p_bus.join()
    except KeyboardInterrupt:
        logger.info("Emergency Stop Initiated...")
        for p in procs + [p_bus]: 
            p.terminate()
            p.join()
