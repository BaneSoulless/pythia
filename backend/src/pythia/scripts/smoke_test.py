"""
Pythia CI Smoke Test
Verifies that the orchestrator starts correctly and loads evolved parameters.
"""
import asyncio
import os
import sys
import logging

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from pythia.infrastructure.orchestrator import PythiaSupervisor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SMOKE-TEST")

async def run_smoke_test():
    logger.info("Initializing PythiaSupervisor...")
    supervisor = PythiaSupervisor()
    
    # 1. Check if config loaded
    params = supervisor.config_provider.params
    if not params or "rl" not in params:
        logger.error("COULD NOT LOAD PYTHIA PARAMS!")
        sys.exit(1)
    
    logger.info(f"Successfully loaded evolved config: {params['metadata']['version']}")
    
    # 2. Check if ASI-Evolve Engine initialized
    if not hasattr(supervisor, "asi_engine") or supervisor.asi_engine is None:
        logger.error("ASI-EVOLVE ENGINE NOT INITIALIZED!")
        sys.exit(1)
    
    logger.info(f"ASI-Evolve Engine ready. Mutation count: {supervisor.asi_engine.mutation_count}")
    
    # 3. Test initialization of services (without blocking gather)
    logger.info("Verifying infrastructure components...")
    assert supervisor.metrics is not None
    assert supervisor.api_app is not None
    assert supervisor.bus is not None
    
    logger.info("✅ Smoke test PASSED: Orchestrator and Evolution Engine ready.")
    sys.exit(0)

if __name__ == "__main__":
    try:
        asyncio.run(run_smoke_test())
    except Exception as exc:
        logger.error(f"❌ Smoke test FAILED: {exc}")
        sys.exit(1)
