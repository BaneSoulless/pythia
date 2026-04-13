"""
Event Store for recording Trade Intents and Market Predictions.
This logs AI predictions independently of whether the order was filled,
providing an immutable history for Brier Score calibration and Model evaluation.
"""

from datetime import UTC, datetime

import structlog
from pythia.infrastructure.persistence.database import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String

logger = structlog.get_logger(__name__)

class PredictionTrace(Base):
    """
    Records every TradeIntent emitted by the Intelligence layer.
    Used exclusively for model evaluation, NOT execution.
    """
    __tablename__ = "prediction_traces"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    market_id = Column(String, index=True, nullable=False)
    outcome_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    agent_probability = Column(Float, nullable=False)
    market_implied_probability = Column(Float, nullable=False)
    rationale = Column(String, nullable=True)

    # Audit trail for learning loops
    is_resolved = Column(Boolean, default=False, nullable=False)
    actual_outcome = Column(Float, nullable=True)  # e.g., 1.0 if YES, 0.0 if NO
    brier_score = Column(Float, nullable=True)

    metadata = Column(JSON, default={})

def log_prediction(db, intent):
    """Safely log the intention to the database using SQLAlchemy."""
    trace = PredictionTrace()
    trace.signal_id = intent.signal_id
    trace.market_id = intent.market_id
    trace.outcome_id = intent.outcome_id
    trace.action = intent.action
    trace.agent_probability = intent.agent_probability
    trace.market_implied_probability = intent.market_implied_probability
    trace.rationale = intent.rationale
    db.add(trace)
    try:
        db.commit()
        db.refresh(trace)
    except Exception as e:
        db.rollback()
        logger.error("Failed to log prediction trace", error=str(e), signal_id=intent.signal_id)
