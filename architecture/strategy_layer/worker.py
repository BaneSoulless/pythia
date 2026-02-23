"""
Strategy Layer - Scalability
Worker Definition for ProcessPoolExecutor
"""
import numpy as np

# Global instance for worker process
_worker_agent = None

def init_worker_process(config):
    """Initialize the RLAgent in the worker process (Lazy Loading TF)."""
    global _worker_agent
    
    # Import here to avoid overhead/conflicts in parent process if possible
    # though scaling.py imports this file which imports nothing heavy.
    from architecture.strategy_layer.agent import RLAgent
    
    # Force TF to use specific visible devices if needed?
    # For now relying on default.
    _worker_agent = RLAgent(config)

def execute_inference_task(state: np.ndarray):
    """Execute prediction using the worker's local agent instance."""
    if _worker_agent is None:
        raise RuntimeError("Worker not initialized")
    
    # We only offload the 'predict' call which is the heavy lifting
    return _worker_agent.engine.predict(state)
