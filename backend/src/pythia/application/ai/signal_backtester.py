"""
Signal Backtester - Evaluation of AI Trading Signals.
Compares probabilistic AI signals with deterministic Technical Analysis (TA) ground truth.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from pythia.application.ai.specialized_agents import TechnicalAnalysisAgent
from pythia.domain.cognitive.models import TradingSignal

logger = logging.getLogger(__name__)


class SignalBacktester:
    """
    Evaluates the accuracy and quality of TradingSignals.
    Part of the AI Control Plane (Module 12+).
    """

    def __init__(self, ta_agent: Optional[TechnicalAnalysisAgent] = None):
        self.ta_agent = ta_agent or TechnicalAnalysisAgent()
        self.history: List[Dict] = []

    def evaluate_signal(
        self, signal: TradingSignal, market_prices: List[float]
    ) -> Dict:
        """
        Compare a single TradingSignal with TA indicators.

        Args:
            signal: The AI-generated signal.
            market_prices: Historical prices at the time of signal generation.

        Returns:
            Evaluation report with 'agreement_score' and 'alignment'.
        """
        if len(market_prices) < 20:
            return {"error": "Insufficient price data for TA ground truth"}

        ta_report = self.ta_agent.analyze_trend(market_prices)
        ta_direction = ta_report["direction"]  # bullish, bearish, neutral

        # Map Signal Action to TA Direction
        action_map = {"BUY": "bullish", "SELL": "bearish", "HOLD": "neutral"}
        expected_direction = action_map.get(signal.action, "neutral")

        agreement = 1.0 if expected_direction == ta_direction else 0.0

        # Soft agreement for divergence
        if expected_direction == "neutral" or ta_direction == "neutral":
             if agreement == 0.0:
                 agreement = 0.3 # Partial penalty for neutral/directional mismatch

        evaluation = {
            "signal_timestamp": datetime.now().isoformat(),
            "pair": signal.pair,
            "ai_action": signal.action,
            "ta_direction": ta_direction,
            "agreement_score": agreement,
            "confidence": signal.confidence,
            "reason": signal.reason,
            "valid": agreement >= 0.7 or signal.confidence < 0.6
        }

        self.history.append(evaluation)
        return evaluation

    def get_aggregate_accuracy(self, window: int = 100) -> float:
        """Calculate mean agreement score over the last N evaluations."""
        recent = self.history[-window:]
        if not recent:
            return 0.0
        return sum(e["agreement_score"] for e in recent) / len(recent)

    def detect_drift(self, threshold: float = 0.5, window: int = 10) -> bool:
        """
        Detects if AI signals significantly diverge from TA ground truth.
        Triggers 'Drift Detected' if accuracy drops below threshold.
        """
        accuracy = self.get_aggregate_accuracy(window=window)
        if len(self.history) >= window and accuracy < threshold:
            logger.warning(
                f"🚨 AI DRIFT DETECTED: Accuracy {accuracy:.2f} < Threshold {threshold}"
            )
            return True
        return False
