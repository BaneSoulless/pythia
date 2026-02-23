import asyncio
import logging
import json
import sys
import os
import pandas as pd

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("Verifier")

# Inject paths (Crucial for importing architecture)
from utils import recursive_dependency_injector
repo_path = os.path.join(os.path.dirname(__file__), 'temp_repos')
recursive_dependency_injector(repo_path)

async def run_verification():
    logger.info("--- STARTING MODULAR SYSTEM VERIFICATION ---")
    
    # 1. Load Config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        logger.info("[PASS] Config loaded")
    except Exception as e:
        logger.error(f"[FAIL] Config load: {e}")
        return

    # 2. Test Architecture Imports & Initialization
    try:
        # DATA LAYER
        from architecture.data_layer.feed import DataPipeline
        data_pipe = DataPipeline(config)
        logger.info(f"[PASS] Data Layer (Buffer: {data_pipe.buffer_size})")
        
        # STRATEGY LAYER
        from architecture.strategy_layer.analytics import StrategyAnalytics
        from architecture.strategy_layer.agent import TransformerAgent
        strat_analytics = StrategyAnalytics(config)
        agent = TransformerAgent(config)
        logger.info("[PASS] Strategy Layer (Analytics & Agent)")
        
        # EXECUTION LAYER
        from architecture.execution_layer.connector import ExchangeConnector
        connector = ExchangeConnector(config)
        logger.info(f"[PASS] Execution Layer (Mode: {config['exchange']['name']})")
        
        # COGNITIVE LAYER (If present)
        try:
            from architecture.cognitive_layer.processor import CognitiveProcessor
            brain = CognitiveProcessor(config)
            agent_count = len(brain.agents_memory)
            if agent_count > 0:
                logger.info(f"[PASS] Cognitive Layer ({agent_count} Agents Loaded)")
            else:
                logger.warning("[WARN] Cognitive Layer loaded but NO AGENTS found (Check folder path)")
        except ImportError:
            logger.warning("[SKIP] Cognitive Layer not found (Module missing)")
            
    except ImportError as e:
        logger.critical(f"[FAIL] Architecture Import Error: {e}")
        return
    except Exception as e:
        logger.critical(f"[FAIL] Module Initialization Error: {e}")
        return

    # 3. Functional Logic Test (Simulate a Tick)
    try:
        logger.info("--- TESTING LOGIC FLOW ---")
        
        # Create Mock Data
        mock_tick = {"symbol": "BTC/USDT", "close": 50000.0, "volume": 1000.0}
        df = data_pipe.process_tick(mock_tick)
        
        # Need history for indicators (duplicate tick to simulate history)
        history = pd.concat([df] * 50, ignore_index=True) 
        
        # Compute Indicators
        analyzed_df = strat_analytics.compute_indicators(history)
        
        if 'rsi' in analyzed_df.columns:
            last_rsi = analyzed_df['rsi'].iloc[-1]
            logger.info(f"[PASS] Indicator Logic: RSI calculated ({last_rsi:.2f})")
        else:
            logger.error("[FAIL] RSI column missing in DataFrame")
            
    except Exception as e:
        logger.error(f"[FAIL] Logic Flow: {e}")

    logger.info("--- VERIFICATION COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(run_verification())
