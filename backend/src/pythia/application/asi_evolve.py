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
                # Monthly target reward override (se env var settata)
                if os.environ.get("ASI_REWARD_FUNCTION") == "monthly_target_reward":
                    metrics = node.results
                    _trade_count = getattr(metrics, 'trade_count', 0) if metrics else 0
                    if _trade_count >= 20:
                        _monthly_ret = getattr(metrics, 'monthly_return', 0.0)
                        _monthly_std = getattr(metrics, 'monthly_std_dev', 0.05)
                        _asset_cls = os.environ.get("ASI_ASSET_CLASS", "CRYPTO")
                        
                        # Calcola sharpe/win/dd dai metadati del nodo se non in metrics
                        _sharpe = getattr(metrics, 'sharpe', node.results.get('sharpe_ratio', 0.0))
                        _win = getattr(metrics, 'win_rate', node.results.get('win_rate', 0.0))
                        _dd = getattr(metrics, 'drawdown', node.results.get('max_drawdown', 0.0))

                        _new_score = ASIEvolveEngine._monthly_target_reward(
                            monthly_return=_monthly_ret,
                            sharpe_ratio=_sharpe,
                            win_rate=_win,
                            max_drawdown=_dd,
                            monthly_std_dev=_monthly_std,
                            asset_class=_asset_cls,
                        )
                        logger.warning(
                            "monthly_target_reward_override",
                            old_score=node.score,
                            new_score=_new_score,
                            trade_count=_trade_count,
                        )
                        node.score = _new_score

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

    def load_evolved_config(self) -> Optional[Dict[str, Any]]:
        """
        Legge pythia_params_evolved.yaml se esiste e non è ancora promoted.
        Usato dal ShadowEvaluator per testare il config evolved in parallelo.
        """
        import yaml
        evolved_path = Path("backend/config/pythia_params_evolved.yaml")
        if not evolved_path.exists():
            return None
        raw = yaml.safe_load(evolved_path.read_text())
        if raw.get("metadata", {}).get("promoted", False):
            return None  # già in produzione, non serve shadow
        return raw

    def record_shadow_trade(self, shadow_win: bool, shadow_pnl: float) -> bool:
        """
        Registra un trade shadow. Restituisce True se la soglia
        per il promote automatico è stata raggiunta.
        Aggiorna shadow_trades_completed in pythia_params_evolved.yaml.
        """
        import yaml
        from datetime import timezone
        evolved_path = Path("backend/config/pythia_params_evolved.yaml")
        if not evolved_path.exists():
            return False

        raw = yaml.safe_load(evolved_path.read_text())
        meta = raw.setdefault("metadata", {})
        completed = meta.get("shadow_trades_completed", 0) + 1
        required = meta.get("shadow_trades_required", 50)
        meta["shadow_trades_completed"] = completed

        # Accumula metriche shadow
        shadow_log = Path("backend/data/shadow_trades.jsonl")
        shadow_log.parent.mkdir(parents=True, exist_ok=True)
        with open(shadow_log, "a") as f:
            f.write(json.dumps({
                "ts": datetime.now(tz=timezone.utc).isoformat(),
                "win": shadow_win,
                "pnl": shadow_pnl,
                "trade_n": completed,
            }) + "\n")

        evolved_path.write_text(yaml.dump(raw, default_flow_style=False))
        logger.info(
            "shadow_trade_recorded",
            extra={"completed": completed, "required": required, "win": shadow_win}
        )
        return completed >= required

    def promote_evolved_config(self) -> bool:
        """
        Promuove pythia_params_evolved.yaml a pythia_params.yaml
        dopo aver verificato le metriche shadow.
        Restituisce True se il promote è avvenuto.
        """
        import yaml
        from datetime import timezone

        evolved_path = Path("backend/config/pythia_params_evolved.yaml")
        prod_path = Path("backend/config/pythia_params.yaml")
        shadow_log = Path("backend/data/shadow_trades.jsonl")

        if not evolved_path.exists() or not shadow_log.exists():
            return False

        # Calcola metriche shadow
        trades = [json.loads(l) for l in shadow_log.read_text().splitlines() if l.strip()]
        if len(trades) < 50:
            logger.warning(f"promote_blocked - reason: insufficient_shadow_trades, count: {len(trades)}")
            return False

        win_rate = sum(1 for t in trades if t.get("win")) / len(trades)
        avg_pnl = sum(t.get("pnl", 0) for t in trades) / len(trades)

        if win_rate < 0.45 or avg_pnl <= 0:
            logger.warning(
                f"promote_blocked - reason: shadow_metrics_below_threshold, win_rate: {win_rate}, avg_pnl: {avg_pnl}"
            )
            return False

        # Backup produzione attuale
        if prod_path.exists():
            backup = prod_path.with_suffix(f".backup_{datetime.now(tz=timezone.utc).strftime('%Y%m%d_%H%M%S')}.yaml")
            prod_path.rename(backup)
            logger.info(f"production_config_backed_up - backup: {str(backup)}")

        # Promote
        raw = yaml.safe_load(evolved_path.read_text())
        raw["metadata"]["promoted"] = True
        raw["metadata"]["promoted_at"] = datetime.now(tz=timezone.utc).isoformat()
        raw["metadata"]["score_source"] = "shadow_validated"
        raw["metadata"]["shadow_win_rate"] = round(win_rate, 4)
        raw["metadata"]["shadow_avg_pnl"] = round(avg_pnl, 6)

        prod_path.write_text(yaml.dump(raw, default_flow_style=False))
        evolved_path.unlink()  # rimuovi shadow file dopo promote
        
        # Archivia il file di log dei shadow trades
        shadow_backup = shadow_log.with_suffix(f".backup_{datetime.now(tz=timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl")
        shadow_log.rename(shadow_backup)

        logger.info(
            f"evolved_config_promoted - win_rate: {win_rate}, avg_pnl: {avg_pnl}, trades: {len(trades)}"
        )
        return True
    @staticmethod
    def _monthly_target_reward(
        monthly_return: float,
        sharpe_ratio: float,
        win_rate: float,
        max_drawdown: float,
        monthly_std_dev: float,
        asset_class: str = "CRYPTO",
    ) -> float:
        """
        Reward function calibrata su target +10%/mese multi-asset.
        
        Componenti:
        - monthly_return: rendimento mensile effettivo (es. 0.12 = 12%)
        - sharpe_ratio: Sharpe annualizzato
        - win_rate: percentuale trade vincenti (es. 0.55 = 55%)
        - max_drawdown: massimo drawdown (es. 0.08 = 8%, positivo)
        - monthly_std_dev: deviazione standard dei ritorni mensili
        - asset_class: CRYPTO | STOCK | PREDICTION_MARKET
        
        Sigmoid centrata su valori target:
        - monthly_return target: 10% → sigmoid(0) = 0.5 (neutro)
        - sopra target → score > 0.5
        - sotto target → score < 0.5
        """
        import math

        def sigmoid(x: float) -> float:
            # Clamp per evitare overflow su input estremi
            x = max(-500.0, min(500.0, x))
            return 1.0 / (1.0 + math.exp(-x))

        monthly_score = sigmoid((monthly_return - 0.10) / 0.02)
        sharpe_score = sigmoid((sharpe_ratio - 1.5) / 0.5)
        win_score = sigmoid((win_rate - 0.50) / 0.05)
        drawdown_score = sigmoid((-max_drawdown + 0.10) / 0.03)
        consistency_score = sigmoid((-monthly_std_dev + 0.05) / 0.02)

        weights = {
            "CRYPTO": {
                "monthly": 0.35, "sharpe": 0.25, "win": 0.20,
                "drawdown": 0.10, "consistency": 0.10,
            },
            "STOCK": {
                "monthly": 0.35, "sharpe": 0.15, "win": 0.15,
                "drawdown": 0.15, "consistency": 0.20,
            },
            "PREDICTION_MARKET": {
                "monthly": 0.35, "sharpe": 0.10, "win": 0.30,
                "drawdown": 0.10, "consistency": 0.15,
            },
        }
        w = weights.get(asset_class.upper(), weights["CRYPTO"])

        score = (
            w["monthly"] * monthly_score
            + w["sharpe"] * sharpe_score
            + w["win"] * win_score
            + w["drawdown"] * drawdown_score
            + w["consistency"] * consistency_score
        )
        return round(score, 6)
