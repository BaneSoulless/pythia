"""
Position Sizing models specifically optimized for Prediction Markets.
Validates ADR-0012: Default Position Sizing Framework for PMs.
"""

from typing import TypedDict

import structlog
from pythia.core.config import settings
from pythia.domain.prediction_markets.models import TradeIntent

logger = structlog.get_logger(__name__)

class SizingResult(TypedDict):
    approved: bool
    allocated_amount: float
    reason: str

def calculate_confidence_weighted_allocation(
    intent: TradeIntent,
    portfolio_balance: float,
    current_exposure: float
) -> SizingResult:
    """
    Allocates capital based on agent confidence.
    Hard limits apply independent of confidence.
    """

    # 1. Base Portfolio checks
    if portfolio_balance < settings.MIN_BALANCE:
        return SizingResult(approved=False, allocated_amount=0.0, reason="Portfolio below MIN_BALANCE")

    # 2. Max correlation/PM exposure cap check (e.g. 10% of total balance max per PM question)
    max_question_exposure = portfolio_balance * 0.10
    if current_exposure >= max_question_exposure:
        return SizingResult(approved=False, allocated_amount=0.0, reason="Max exposure reached for this PM")

    # 3. Base Trade Sizing (Fixed fractional)
    base_trade_amount = portfolio_balance * settings.RISK_PER_TRADE

    # Cap single trade by absolute limit
    base_trade_amount = min(base_trade_amount, settings.MAX_POSITION_SIZE)

    # 4. Confidence Scalar (0.5 to 1.0 confidence maps to 0% to 100% of base amount)
    # The agent confidence gate forces intent confidence >= 0.5.
    if intent.confidence < 0.5:
        return SizingResult(approved=False, allocated_amount=0.0, reason="Confidence score below 0.5 strict limit")

    # Scale: confidence 0.5 -> scalar 0; confidence 1.0 -> scalar 1.0
    confidence_scalar = (intent.confidence - 0.5) * 2.0

    allocated = round(float(base_trade_amount * confidence_scalar), 2)

    # 5. Adjusted space check
    remaining_capacity = max_question_exposure - current_exposure
    final_allocation = min(allocated, remaining_capacity)

    if final_allocation <= 0.0:
        return SizingResult(approved=False, allocated_amount=0.0, reason="Allocation calculated as <= zero")

    return SizingResult(approved=True, allocated_amount=final_allocation, reason="Approved by Confidence model")
