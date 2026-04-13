from typing import Literal

from pydantic import BaseModel, model_validator


class TradingSignal(BaseModel):
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float  # 0.0-1.0
    pair: str
    stop_loss_pct: float = 0.02
    reason: str

    @model_validator(mode="after")
    def confidence_gate(self) -> 'TradingSignal':
        """Confidence Gate: < 0.5 -> force HOLD via model_validator."""
        if self.confidence < 0.5 and self.action != "HOLD":
            self.action = "HOLD"
        return self
