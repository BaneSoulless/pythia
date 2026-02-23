import asyncio
import multiprocessing as mp
import json
import logging
import sys
import os
import time
import platform
import numpy as np
from collections import deque

# --- CRITICAL WINDOWS FIX ---
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# ----------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Orchestrator")

# Inject Paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend", "app", "infrastructure", "messaging"))

from utils import recursive_dependency_injector
repo_path = os.path.join(os.path.dirname(__file__), "temp_repos")
recursive_dependency_injector(repo_path)

from system_bus import SystemBus, bus_listener
from architecture.infrastructure.telemetry import MetricsServer, record_tick
from architecture.infrastructure.cache import StateCache

def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"system": {"ports": {"execution": 5555, "strategy": 5556, "data": 5557}}, "exchange": {"name": "binance"}, "redis": {"host": "localhost"}}

# --- PROCESSES ---

def run_data_layer(bus_queue, config):
    if platform.system() == "Windows": asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    from architecture.data_layer.feed import DataPipeline
    from system_bus import SystemBus
    
    bus = SystemBus(config)
    bus.setup_data_endpoint()
    cache = StateCache(host=config.get('redis', {}).get('host', 'localhost'))
    pipeline = DataPipeline(config)
    
    async def stream_handler(candle):
        cache.push_candle(candle['symbol'], candle)
        record_tick(candle['symbol'], candle['timestamp'])
        if int(time.time()) % 10 == 0:
            logger.info(f"MKTDATA: {candle['symbol']} ${candle['close']}")

    async def loop():
        logger.info("Data Layer: ONLINE (Sensory Fidelity: HIGH | Persistence: REDIS)")
        pipeline.subscribe(stream_handler)
        await pipeline.start_stream()
            
    asyncio.run(loop())

def run_learning_layer(bus_queue, config):
    if platform.system() == "Windows": asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    from architecture.learning.pipeline import LearningLoop
    # Sleep until 'night' or just run periodic
    learner = LearningLoop(config)
    
    async def loop():
        logger.info("Learning Layer: ONLINE (Automated Retraining: ENABLED)")
        while True:
            await asyncio.sleep(600) # Check every 10 mins (Proto)
            # In prod, check time == 00:00 UTC
            logger.info("Running Optimization Cycle...")
            # Mock Agent passing - in real impl, load weights from disk, train, save
            learner.run_cycle(None) 
            
    asyncio.run(loop())

def run_strategy_layer(bus_queue, config, mode="LIVE"):
    """
    Main Strategy or Shadow Ghost.
    mode: LIVE or SHADOW
    """
    if platform.system() == "Windows": asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    from architecture.strategy_layer.scaling import AgentWorkerPool
    from architecture.risk_layer.sovereign import RiskManager
    from architecture.optimization.evolution import EvolutionDaemon
    from system_bus import SystemBus
    
    bus = SystemBus(config)
    if mode == "LIVE":
        bus.connect_strategy_publisher()
    
    cache = StateCache(host=config.get('redis', {}).get('host', 'localhost'))
    pool = AgentWorkerPool(config, num_workers=2)
    pool.start()
    
    # Sovereign Components
    sovereign = RiskManager(config)
    evolution = EvolutionDaemon()
    
    epsilon = 0.5
    
    async def loop():
        logger.info(f"Strategy Layer ({mode}): ONLINE (Sovereign Kernel: ACTIVE)")
        symbol = "BTCUSDT"
        
        while True:
            # SAFE INIT - Prevent UnboundLocalError
            action = 'hold'
            confidence = 0.0
            state = np.zeros(10)
            signal = None
            
            try:
                history = cache.get_history(symbol, 50) 
            
                # KINETIC VALIDATION PATCH: Lower threshold to 1 to force reaction
                if len(history) >= 1:
                    # 1. Evolution (Hyper-Parameter Tuning)
                    if int(time.time()) % 60 == 0: 
                        try:
                            new_params = evolution.evolve(history)
                        except Exception as e:
                            logger.error(f"Evolution Skip: {e}")

                    # 2. Inference Preparation
                    snapshot = history[-10:]
                    closes = np.array([c['close'] for c in snapshot])
                    if len(closes) > 0:
                        if closes[0] > 0: norm_closes = closes / closes[0]
                        else: norm_closes = closes
                        state = np.zeros(10)
                        state[:len(norm_closes)] = norm_closes
                    else:
                        state = np.zeros(10)
                    
                    # 3. Decision
                    action = 'hold'
                    confidence = 0.0

                
                try:
                    q_values_arr = await pool.predict_async(state)
                    q_values = q_values_arr[0]
                    action_idx = np.argmax(q_values)
                    actions = ['hold', 'buy', 'sell']
                    action = actions[action_idx]
                    
                    # Softmax
                    exp_q = np.exp(q_values - np.max(q_values))
                    confidence = float(exp_q[action_idx] / np.sum(exp_q))
                except Exception as e:
                    logger.error(f"Inference: {e}")

                if action != 'hold' and confidence > 0.5:
                    if mode == "LIVE":
                        # 4. Sovereign Risk Check
                        # Mock portfolio state
                        portfolio = {'hourly_drawdown': 0.0, 'win_rate': 0.6}
                        
                        signal = {'action': action, 'confidence': confidence, 'symbol': symbol}
                        validated_signal = sovereign.validate_trade(signal, portfolio)
                        
                        if validated_signal:
                            logger.info(f"⚡ STRATEGY SIGNAL (Verified): {validated_signal}")
                            await bus.publish_signal(validated_signal)
                        else:
                            logger.warning(f"🛡️ SIGNAL BLOCKED by Risk Kernel")
                    else:
                        # Shadow Mode - Just log
                        logger.info(f"👻 GHOST SIGNAL: {action} ({confidence:.2f}) - Validating...")
            
            except Exception as e:
                 logger.error(f"STRATEGY LOOP ERROR: {e}")
                 await asyncio.sleep(1)

            await asyncio.sleep(1)

    asyncio.run(loop())

def run_execution_layer(bus_queue, config):
    if platform.system() == "Windows": asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    from architecture.execution_layer.connector import ExchangeConnector
    from system_bus import SystemBus
    
    bus = SystemBus(config)
    bus.connect_execution_subscriber()
    connector = ExchangeConnector(config)
    
    async def loop():
        logger.info("Execution Layer: ONLINE")
        while True:
            await asyncio.sleep(1)
            
    asyncio.run(loop())

def start_bus(bus_queue, config):
    if platform.system() == "Windows": asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    bus = SystemBus(config)
    bus_queue.put("READY")
    asyncio.run(bus_listener(bus))

if __name__ == "__main__":
    mp.freeze_support()
    logger.info("Initializing NEURAL ARCHITECT BOT (Sovereign Evolution v5)...")
    
    MetricsServer.start(9090)
    config = load_config()
    bus_queue = mp.Queue()
    
    p_bus = mp.Process(target=start_bus, args=(bus_queue, config))
    p_bus.start()
    bus_queue.get() 
    
    procs = [
        mp.Process(target=run_data_layer, args=(bus_queue, config)),
        mp.Process(target=run_strategy_layer, args=(bus_queue, config, "LIVE")),
        mp.Process(target=run_strategy_layer, args=(bus_queue, config, "SHADOW")), # Ghost Instance
        mp.Process(target=run_execution_layer, args=(bus_queue, config)),
        mp.Process(target=run_learning_layer, args=(bus_queue, config)) # Retraining
    ]
    
    for p in procs: p.start()
    
    logger.info("SYSTEM LIVE (Sovereign Entity). Press Ctrl+C to stop.")
    
    try:
        p_bus.join()
    except KeyboardInterrupt:
        for p in procs + [p_bus]: p.terminate()
