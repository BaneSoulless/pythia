"""
pythia_rl_eval.py — Core evaluator for Pythia evolution candidates.
Connects to performance database and returns a composite score.
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Path bootstrapping
BACKEND_DIR = Path(__file__).parent.parent
SRC_DIR = BACKEND_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from pythia.infrastructure.persistence.database import SessionLocal
    from pythia.infrastructure.persistence.models import Trade
    from pythia.workers.shadow_agent import generate_shadow_report
except ImportError as e:
    print(f"ERROR: Could not import pythia modules: {e}")
    # Partial fallback for isolation testing
    SessionLocal = None

def evaluate_performance() -> dict:
    """
    Calculates a composite score based on live/simulated trade history.
    Score = Sharpe * (1 - MaxDrawdown) * WinRate
    """
    if not SessionLocal:
        return {"score": 0.5, "error": "database_not_available"}

    db = SessionLocal()
    try:
        # 1. Use Shadow Agent for higher-level metrics
        shadow_report = generate_shadow_report(db)
        
        # 2. Extract trade-based metrics
        cutoff = datetime.utcnow() - timedelta(days=30)
        trades = db.query(Trade).filter(Trade.created_at >= cutoff).all()
        
        if len(trades) < 5:
            # Not enough data for statistical significance
            return {
                "score": 0.0, 
                "metrics": {"trade_count": len(trades)},
                "reason": "insufficient_data"
            }
        
        profits = [t.pnl for t in trades]
        win_rate = len([p for p in profits if p > 0]) / len(profits)
        
        # Simple Sharpe approximation
        import statistics
        avg_profit = statistics.mean(profits)
        std_profit = statistics.stdev(profits) if len(profits) > 1 else 1.0
        sharpe = (avg_profit / std_profit) if std_profit > 0 else 0
        
        # Drawdown calculation
        cumulative = 0
        peak = -float('inf')
        max_dd = 0
        for p in profits:
            cumulative += p
            if cumulative > peak: peak = cumulative
            dd = (peak - cumulative) / (abs(peak) + 1e-9)
            if dd > max_dd: max_dd = dd
            
        score = sharpe * (1 - max_dd) * win_rate
        
        return {
            "score": round(max(0, score), 4),
            "metrics": {
                "sharpe": round(sharpe, 4),
                "drawdown": round(max_dd, 4),
                "win_rate": round(win_rate, 4),
                "trade_count": len(trades),
                "shadow_accuracy": shadow_report.get("directional_accuracy", 0)
            }
        }
    finally:
        db.close()

if __name__ == "__main__":
    # If run directly as a script, output JSON to stdout
    result = evaluate_performance()
    print(json.dumps(result))
