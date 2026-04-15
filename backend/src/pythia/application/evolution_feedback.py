import logging
import os
import subprocess
import json
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import text

logger = logging.getLogger("PYTHIA-EVO-FEEDBACK")

class EvolutionFeedbackScheduler:
    """
    Schedules and triggers re-evolution cycles based on paper trading performance.
    
    Trigger conditions:
    - 50 paper trades completed
    - 30 days since last evolution (simulated via threshold)
    - Monthly score below target + threshold
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.min_trades = 50
        self.feedback_interval_days = 30
        self.warmstart_path = "backend/config/warmstart_trades.json"

    def check_and_trigger(self) -> Dict[str, Any]:
        """
        Main entry point for checking evolution status.
        Called by PaperTradingBroker after trade closure.
        """
        try:
            # 1. Fetch trade count
            res = self.db.execute(text("SELECT COUNT(*) FROM paper_trades")).fetchone()
            trade_count = res[0] if res else 0
            
            # 2. Fetch latest monthly performance
            res = self.db.execute(
                text("SELECT monthly_return, sharpe_ratio FROM monthly_target_log ORDER BY id DESC LIMIT 1")
            ).fetchone()
            
            monthly_ret = res[0] if res else 0.0
            sharpe = res[1] if res else 0.0
            
            logger.info(
                f"Evolution feedback check: trades={trade_count}, monthly_ret={monthly_ret}, sharpe={sharpe}"
            )

            # 3. Check trigger condition
            if trade_count >= self.min_trades:
                logger.warning("triggering_reevolution - reason: trade_count_threshold_met")
                
                # Export trades for warmstart
                self._export_warmstart_data()
                
                # Record trigger in DB
                self._record_reevolution_trigger(
                    reason=f"automatic_refinement_{trade_count}_trades",
                    trade_count=trade_count,
                    monthly_ret=monthly_ret
                )
                
                # Launch async subprocess
                self._launch_reevolution_async()
                
                return {
                    "triggered": True,
                    "reason": "trade_count_threshold",
                    "trade_count": trade_count
                }

            return {"triggered": False, "trade_count": trade_count}

        except Exception as e:
            logger.error(f"Evolution feedback error: {str(e)}")
            return {"triggered": False, "error": str(e)}

    def _export_warmstart_data(self):
        """Exports recent paper trades to JSON for the evolution engine."""
        try:
            res = self.db.execute(text("SELECT * FROM paper_trades ORDER BY closed_at DESC LIMIT 200"))
            # Use mappings() to get dict-like rows in SQLAlchemy 2.0+
            trades = [dict(row) for row in res.mappings()]
            
            # Serialize datetimes
            for t in trades:
                for k, v in t.items():
                    if isinstance(v, datetime):
                        t[k] = v.isoformat()

            os.makedirs(os.path.dirname(self.warmstart_path), exist_ok=True)
            with open(self.warmstart_path, "w") as f:
                json.dump(trades, f, indent=2)
            
            logger.info(f"Warmstart data exported to {self.warmstart_path} (count: {len(trades)})")
        except Exception as e:
            logger.error(f"Warmstart export failed: {str(e)}")

    def _record_reevolution_trigger(self, reason: str, trade_count: int, monthly_ret: float):
        """Persists the trigger event to the evolution_runs table."""
        try:
            self.db.execute(
                text("""
                    INSERT INTO evolution_runs 
                    (triggered_at, trigger_reason, warmstart_path, trade_count_at_trigger, monthly_return_at_trigger, status)
                    VALUES (:ts, :reason, :path, :trades, :ret, 'pending')
                """),
                {
                    "ts": datetime.now(timezone.utc),
                    "reason": reason,
                    "path": self.warmstart_path,
                    "trades": trade_count,
                    "ret": monthly_ret
                }
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"DB record trigger failed: {str(e)}")

    def _launch_reevolution_async(self):
        """
        Spawns the re-run script in a non-blocking subprocess with background logging.
        Uses subprocess.Popen for asynchronous execution on Windows/Linux.
        """
        cmd = [
            "python", "scripts/asi_rerun_with_real_data.py",
            "--run",
            "--warmstart", self.warmstart_path,
            "--reward", "monthly_target_reward"
        ]
        
        log_file_path = os.path.join("backend", "logs", "evolution_rerun.log")
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        
        try:
            # Use subprocess.DEVNULL for stdin to avoid blocking if the script expects input
            # Redirect stdout/stderr to the log file
            log_handle = open(log_file_path, "a")
            log_handle.write(f"\n--- Spawning Evolution Re-run at {datetime.now().isoformat()} ---\n")
            log_handle.flush()
            
            proc = subprocess.Popen(
                cmd,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                env=os.environ.copy(),
                cwd=os.getcwd()
            )
            
            logger.warning(
                f"Re-evolution subprocess spawned (PID: {proc.pid}) tracking log in {log_file_path}"
            )
            # Note: handle remains open in the subprocess until it exits
        except Exception as e:
            logger.error(f"Re-evolution spawn failed: {str(e)}")
