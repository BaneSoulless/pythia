from typing import Literal
from pydantic import BaseModel, field_validator

class TradingSignal(BaseModel):
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float  # 0.0-1.0
    pair: str
    stop_loss_pct: float = 0.02
    reason: str
    
    @field_validator("action", mode="after")
    @classmethod
    def confidence_gate(cls, action, info):
        """Confidence Gate: < 0.5 -> force HOLD via model_validator."""
        confidence = info.data.get("confidence", 0)
        # In pydantic v2 `info.data` might be `info` if using older version,
        # but modern pydantic uses ValidationInfo.
        # Fallback se non presente in info.data:
        if isinstance(confidence, float):
             if confidence < 0.5 and action != "HOLD":
                 return "HOLD"
        return action
