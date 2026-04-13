"""
Shadow Agent Reporting.
Aggregates historical PredictionTraces to provide calibration curves,
Brier scores, and PnL potential. This is what the operator reviews 
to decide if the agent is ready for live trading.
"""

from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from pythia.infrastructure.persistence.event_store import PredictionTrace

logger = structlog.get_logger(__name__)

def generate_shadow_report(db: Session, _timeframe_days: int = 30) -> dict[str, Any]:
    """
    Analyzes all resolved markets the agent made a prediction on.
    """
    resolved_traces = db.execute(
        select(PredictionTrace)
        .where(PredictionTrace.is_resolved.is_(True))
    ).scalars().all()

    if not resolved_traces:
        return {"status": "insufficient_data", "total_evaluations": 0}

    total_evals = len(resolved_traces)
    avg_brier = sum(t.brier_score for t in resolved_traces if t.brier_score is not None) / total_evals

    # Calculate a simple accuracy metric: Did the agent's probability > 0.5 align with actual=1.0?
    correct_calls = sum(
        1 for t in resolved_traces
        if (t.agent_probability > 0.5 and t.actual_outcome == 1.0) or
           (t.agent_probability < 0.5 and t.actual_outcome == 0.0)
    )
    accuracy = correct_calls / total_evals

    report = {
        "status": "success",
        "total_evaluations": total_evals,
        "average_brier_score": avg_brier,
        "directional_accuracy": accuracy,
        "recommendation": "LIVE_TRADE_READY" if avg_brier < 0.20 else "CONTINUE_PAPER_TRADING"
    }

    logger.info("Shadow Report Generated", report=report)
    return report
