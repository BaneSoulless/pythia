"""
Domain models for Prediction Markets (e.g., Polymarket, Kalshi).
Reflects the binary or multi-categorical nature of these markets, independent of any specific exchange format.
"""

from typing import Literal

from pydantic import BaseModel, Field


class Outcome(BaseModel):
    """A specific outcome for a PM question (e.g., 'Yes', 'No', 'Candidate A')."""
    id: str
    title: str
    implied_probability: float = Field(ge=0.0, le=1.0, description="Current market odds (0 to 1).")
    price: float = Field(ge=0.0, description="Cost per share/token in base currency.")


class Question(BaseModel):
    """A prediction market question."""
    id: str
    title: str
    description: str | None = None
    category: str | None = None
    outcomes: list[Outcome]
    is_resolved: bool = False
    resolution_source: str | None = None
    volume: float = 0.0
    liquidity: float = 0.0


class TradeIntent(BaseModel):
    """
    An intent emitted by the Intelligence layer, representing a desired position.
    This is passed to the Execution layer, decoupled from DB/Wallet context.
    """
    signal_id: str
    market_id: str
    outcome_id: str
    action: Literal["BUY", "SELL"]
    confidence: float = Field(ge=0.0, le=1.0)
    agent_probability: float = Field(ge=0.0, le=1.0, description="Agent's calculated true probability.")
    market_implied_probability: float = Field(ge=0.0, le=1.0, description="Market probability at the time of intent.")
    rationale: str
    max_slippage: float = Field(default=0.02, description="Max acceptable slippage limit.")
