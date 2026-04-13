from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal

class SignalPayload(BaseModel):
    """
    Immutabile DTO che rappresenta la decisione scaturita dal Signal Generation
    e dal Meta-Labeling ML.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)
    
    symbol: str = Field(pattern=r"^[A-Z0-9_]+$")
    base_signal: bool
    ml_confidence: Decimal = Field(ge=0, le=1)
    timestamp: int
