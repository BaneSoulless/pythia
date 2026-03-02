"""
Test script for Phase 3: AI Control Plane.
Verifies SignalBacktester and Drift Detection.
"""

import unittest
from pythia.application.ai.signal_backtester import SignalBacktester
from pythia.domain.cognitive.models import TradingSignal

class TestAIControlPlane(unittest.TestCase):
    def setUp(self):
        self.backtester = SignalBacktester()

    def test_signal_evaluation_agreement(self):
        # Bullish trend (increasing prices)
        prices = [100.0 + i for i in range(25)]
        signal = TradingSignal(
            action="BUY",
            confidence=0.9,
            pair="BTC/USDT",
            reason="Artificial growth"
        )
        report = self.backtester.evaluate_signal(signal, prices)
        self.assertEqual(report["agreement_score"], 1.0)
        self.assertEqual(report["ta_direction"], "bullish")

    def test_drift_detection(self):
        # Force 10 disagreeing signals
        prices = [100.0 for _ in range(25)] # Neutral trend
        signal = TradingSignal(
            action="BUY", # BUY vs Neutral -> Disagree
            confidence=0.9,
            pair="BTC/USDT",
            reason="Drift simulation"
        )
        for _ in range(10):
            self.backtester.evaluate_signal(signal, prices)
        
        self.assertTrue(self.backtester.detect_drift(threshold=0.5, window=10))

if __name__ == "__main__":
    unittest.main()
