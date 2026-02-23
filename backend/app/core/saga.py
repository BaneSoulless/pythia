"""
Saga Pattern Coordinator
SOTA 2026 Distributed Consistency

Manages distributed transactions with compensation logic (Rollback).
"""

import logging
import uuid
from typing import Callable, Any, List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SagaStep:
    name: str
    action: Callable[..., Any]
    compensation: Callable[..., Any]
    args: tuple = ()
    kwargs: dict = None

class SagaError(Exception):
    pass

class SagaCoordinator:
    """
    Executes a sequence of steps. If any step fails, executes compensations
    in reverse order for all completed steps.
    """
    def __init__(self, saga_id: str = None):
        self.saga_id = saga_id or str(uuid.uuid4())
        self.steps: List[SagaStep] = []
        self.completed_steps: List[SagaStep] = []

    def add_step(self, name: str, action: Callable, compensation: Callable, *args, **kwargs):
        """Register a step in the saga."""
        step = SagaStep(name, action, compensation, args, kwargs or {})
        self.steps.append(step)

    async def execute(self):
        """Run the saga."""
        logger.info(f"Starting Saga {self.saga_id} with {len(self.steps)} steps.")
        
        try:
            for step in self.steps:
                logger.debug(f"Saga {self.saga_id}: Executing step '{step.name}'")
                await step.action(*step.args, **step.kwargs)
                self.completed_steps.append(step)
                
            logger.info(f"Saga {self.saga_id} compelted successfully.")
            
        except Exception as e:
            logger.error(f"Saga {self.saga_id} failed at step '{step.name}': {e}")
            logger.info(f"Saga {self.saga_id}: Initiating Rollback (Compensation).")
            await self._compensate()
            raise SagaError(f"Saga failed: {e}")

    async def _compensate(self):
        """Execute compensations in reverse order."""
        for step in reversed(self.completed_steps):
            try:
                logger.debug(f"Saga {self.saga_id}: Compensating step '{step.name}'")
                await step.compensation(*step.args, **step.kwargs)
            except Exception as e:
                # Critical: Compensation failed. Manual intervention needed.
                logger.critical(f"Saga {self.saga_id}: Compensation failed for '{step.name}': {e}")
