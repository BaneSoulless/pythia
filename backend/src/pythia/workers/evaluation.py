"""
Offline Evaluation Jobs for the AI Trading Bot.
Extracts resolved Prediction Market outcomes to calculate
Brier Scores on past Agent predictions cleanly isolated from execution logic.
"""

from typing import Any

import structlog

from pythia.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

def calculate_brier_score(predicted_prob: float, actual_outcome: float) -> float:
    """
    Standard strict Brier score: (predicted - actual)^2
    Best: 0.0 | Worst: 1.0
    """
    return (predicted_prob - actual_outcome) ** 2


@celery_app.task(name="pythia.workers.evaluation.score_resolved_markets")
def score_resolved_markets_task(market_resolution_data: dict[str, Any]) -> dict[str, Any]:
    """
    Called when a Polymarket/Kalshi market officially resolves.
    Finds all predictions for this market and grades them.
    market_resolution_data should contain:
    - market_id
    - winning_outcome_id
    """
    # Note: In a real system, you'd pull the async DB session via dependencies.
    # Here mapped out for structural scaffolding.

    market_id = market_resolution_data["market_id"]
    winning_outcome_id = market_resolution_data["winning_outcome_id"]

    logger.info("Evaluating market resolution", market_id=market_id, winning_outcome_id=winning_outcome_id)

    # Example DB Loop (Pseudo-code context)
    # traces = db.execute(select(PredictionTrace).where(PredictionTrace.market_id == market_id)).scalars().all()
    # for trace in traces:
    #     actual = 1.0 if trace.outcome_id == winning_outcome_id else 0.0
    #     trace.actual_outcome = actual
    #     trace.brier_score = calculate_brier_score(trace.agent_probability, actual)
    #     trace.is_resolved = True
    # db.commit()

    logger.info("Evaluated predictions for market", market_id=market_id)

    return {"status": "success", "market": market_id}
