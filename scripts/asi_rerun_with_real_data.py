#!/usr/bin/env python3
"""
asi_rerun_with_real_data.py
Triggers a new ASI-Evolve run once sufficient real trade data exists.
Run manually or via cron after paper trading period.

Usage:
  python scripts/asi_rerun_with_real_data.py --check   # verifica disponibilità dati
  python scripts/asi_rerun_with_real_data.py --run     # lancia evolution se dati ok
  python scripts/asi_rerun_with_real_data.py --force   # lancia anche senza dati sufficienti
"""
from __future__ import annotations
import argparse
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "backend" / "data" / "pythia_prod.db"
ASI_ROOT = ROOT / "vendor" / "asi_evolve"
MIN_TRADES = 50
MIN_DAYS = 7


def check_data_readiness() -> dict:
    """Verifica se ci sono abbastanza trade reali per una evolution significativa."""
    if not DB_PATH.exists():
        return {"ready": False, "reason": "DB_NOT_FOUND", "trades": 0}

    conn = sqlite3.connect(DB_PATH)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=MIN_DAYS)).isoformat()

    try:
        rows = conn.execute(
            "SELECT COUNT(*) FROM trades WHERE closed_at > ?", (cutoff,)
        ).fetchone()
        count = rows[0] if rows else 0
    except Exception as e:
        return {"ready": False, "reason": f"DB_ERROR: {e}", "trades": 0}
    finally:
        conn.close()

    if count < MIN_TRADES:
        return {
            "ready": False,
            "reason": f"INSUFFICIENT_TRADES: {count}/{MIN_TRADES}",
            "trades": count,
        }

    return {"ready": True, "trades": count, "lookback_days": MIN_DAYS}


def run_evolution(steps: int = 40, sample_n: int = 5) -> int:
    """Lancia ASI-Evolve con i parametri di produzione."""
    eval_sh = ASI_ROOT / "experiments" / "pythia_rl_evolve" / "eval.sh"
    cmd = [
        sys.executable, str(ASI_ROOT / "main.py"),
        "--experiment", "pythia_rl_evolve",
        "--steps", str(steps),
        "--sample-n", str(sample_n),
        "--eval-script", str(eval_sh),
    ]
    print(f"[RUN] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ASI_ROOT))
    return result.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--steps", type=int, default=40)
    args = parser.parse_args()

    status = check_data_readiness()
    print(f"[DATA] {status}")

    if args.check:
        sys.exit(0 if status["ready"] else 1)

    if args.run or args.force:
        if not status["ready"] and not args.force:
            print(f"[BLOCKED] {status['reason']} — use --force to override")
            sys.exit(1)
        rc = run_evolution(steps=args.steps)
        sys.exit(rc)
