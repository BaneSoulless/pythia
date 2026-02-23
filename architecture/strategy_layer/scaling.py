"""
Strategy Layer - Scalability
Horizontal Hyper-Scalability: Agent Worker Pool
"""
import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
from typing import Optional, Dict, Any
import numpy as np

from architecture.strategy_layer.worker import init_worker_process, execute_inference_task

logger = logging.getLogger("StrategyScaling")

class AgentWorkerPool:
    """
    Manages a pool of persistent worker processes for parallel inference.
    Enables non-blocking analysis of 50+ pairs.
    """
    def __init__(self, config: Dict[str, Any], num_workers: int = 4):
        self.config = config
        self.num_workers = num_workers
        self.executor = None
        
    def start(self):
        """Start the process pool."""
        logger.info(f"Initializing Strategy Pool with {self.num_workers} workers...")
        self.executor = ProcessPoolExecutor(
            max_workers=self.num_workers,
            initializer=init_worker_process,
            initargs=(self.config,)
        )
        logger.info("Strategy Pool READY.")

    async def predict_async(self, state: np.ndarray) -> np.ndarray:
        """
        Offload inference to worker pool.
        Returns q_values array.
        """
        if not self.executor:
            raise RuntimeError("Pool not started")
            
        loop = asyncio.get_running_loop()
        # Non-blocking await
        result = await loop.run_in_executor(
            self.executor, 
            execute_inference_task, 
            state
        )
        return result

    def shutdown(self):
        if self.executor:
            self.executor.shutdown(wait=True)
            logger.info("Strategy Pool Terminated.")
