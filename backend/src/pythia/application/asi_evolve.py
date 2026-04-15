import asyncio
import logging
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Core imports
from pythia.domain.events.domain_events import AsiEvolveEvent
from pythia.infrastructure.monitoring.prometheus_exporter import get_metrics_exporter

# Import upstream Pipeline
from asi_evolve.pipeline.main import Pipeline

logger = logging.getLogger("PYTHIA-ASI-EVOLVE")

class ASIEvolveEngine:
    """
    Business service for autonomous parameter evolution.
    Wraps the ASI-Evolve Pipeline and integrates with Pythia's EventBus.
    """

    def __init__(self, event_bus: Any, dry_run: bool = True):
        self.event_bus = event_bus
        self.dry_run = dry_run
        self.enabled = True
        
        # Performance thresholds for triggers
        self.min_sharpe = 1.5
        self.max_drawdown = 0.15
        self.min_trades = 50
        
        # Paths
        self.asi_root = Path(__file__).parent.parent.parent.parent.parent / "vendor" / "asi_evolve"
        self.config_path = self.asi_root / "experiments" / "pythia_rl_evolve" / "config.yaml"
        
        # Initialize Upstream Pipeline (with database access)
        self.pipeline = Pipeline(
            config_path=str(self.config_path),
            experiment_name="pythia_rl_evolve"
        )
        
        # State tracking
        self.mutation_count = len(self.pipeline.database)
        self.last_evolution: Optional[datetime] = None
        self.last_cycle_status = "idle"
        self.cooldown_remaining = 0
        self.metrics_exporter = get_metrics_exporter()
        
        logger.info(f"ASI-Evolve Engine initialized. Mutations: {self.mutation_count}")

    def should_evolve(self, metrics: Dict[str, Any]) -> bool:
        """Determines if a new evolution cycle is required based on performance."""
        if not self.enabled: return False
        
        trade_count = metrics.get("trade_count", 0)
        sharpe = metrics.get("sharpe", 0.0)
        drawdown = metrics.get("drawdown", 0.0)
        
        if trade_count < self.min_trades:
            logger.info(f"Evolution skipped: insufficient data ({trade_count} < {self.min_trades})")
            return False
            
        if sharpe < self.min_sharpe:
            logger.info(f"Evolution triggered: Sharpe {sharpe:.2f} < {self.min_sharpe}")
            return True
            
        if drawdown > self.max_drawdown:
            logger.info(f"Evolution triggered: Drawdown {drawdown:.2f} > {self.max_drawdown}")
            return True
            
        return False

    async def run_cycle(self, force: bool = False):
        """Executes evolution step and publishes results."""
        if not self.enabled or (self.cooldown_remaining > 0 and not force):
            return

        self.last_cycle_status = "running"
        try:
            loop = asyncio.get_running_loop()
            node = await loop.run_in_executor(
                None, 
                self.pipeline.run_step,
                "Improve model robustness for high volatility regimes.",
                str(self.asi_root / "experiments" / "pythia_rl_evolve" / "eval.sh")
            )
            
            if node:
                self.mutation_count += 1
                self.last_evolution = datetime.now()
                self.last_cycle_status = "success"
                
                # Report to Prometheus
                self.metrics_exporter.record_asi_mutation(node.score)
                
                # Publish Domain Event
                if self.event_bus:
                    event = AsiEvolveEvent(
                        node_id=node.id,
                        score=node.score,
                        motivation=node.motivation,
                        version=f"v{self.mutation_count}"
                    )
                    await self.event_bus.publish_signal(event)
                    
                # Audit log (JSONL)
                self._write_audit_log(node)
                
            else:
                self.last_cycle_status = "failed"
        except Exception as exc:
            self.last_cycle_status = f"error: {str(exc)}"
            logger.error(f"Evolution cycle failed: {exc}", exc_info=True)
        finally:
            self.cooldown_remaining = 14400 # 4h

    def _write_audit_log(self, node: Any):
        """Persists mutation details to a local audit file (EDGE-7 candidate)."""
        log_file = Path("backend/data/asi_evolution_audit.jsonl")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "node_id": node.id,
            "score": node.score,
            "motivation": node.motivation,
            "code_hash": hash(node.code)
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "dry_run": self.dry_run,
            "last_cycle_status": self.last_cycle_status,
            "cooldown_remaining": self.cooldown_remaining,
            "mutation_count": self.mutation_count,
            "last_evolution": self.last_evolution.isoformat() if self.last_evolution else None
        }
