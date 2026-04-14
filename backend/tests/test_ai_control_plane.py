"""
Test script for Phase 3: AI Control Plane.
Verifies SignalBacktester, Drift Detection, and MLMetaGate inference.
"""

import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from pythia.application.ai.signal_backtester import SignalBacktester
from pythia.core.errors import ErrorCode, MLGateError
from pythia.domain.cognitive.models import TradingSignal


class TestAIControlPlane(unittest.TestCase):
    def setUp(self):
        self.backtester = SignalBacktester()

    def test_signal_evaluation_agreement(self):
        # Bullish trend (increasing prices)
        prices = [100.0 + i for i in range(25)]
        signal = TradingSignal(
            action="BUY", confidence=0.9, pair="BTC/USDT", reason="Artificial growth"
        )
        report = self.backtester.evaluate_signal(signal, prices)
        self.assertEqual(report["agreement_score"], 1.0)
        self.assertEqual(report["ta_direction"], "bullish")

    def test_drift_detection(self):
        # Force 10 disagreeing signals
        prices = [100.0 for _ in range(25)]  # Neutral trend
        signal = TradingSignal(
            action="BUY",  # BUY vs Neutral -> Disagree
            confidence=0.9,
            pair="BTC/USDT",
            reason="Drift simulation",
        )
        for _ in range(10):
            self.backtester.evaluate_signal(signal, prices)

        self.assertTrue(self.backtester.detect_drift(threshold=0.5, window=10))


# ── MLMetaGate Tests ───────────────────────────────────────────────────────


class TestMLMetaGate:
    """Validate MLMetaGate inference, error handling, and edge cases."""

    def _make_signal_df(self, n: int = 5, bullish: bool = True):
        """Build a DataFrame that triggers base_mask when bullish=True."""
        return pd.DataFrame({
            "rsi": [50.0] * n if bullish else [80.0] * n,
            "ema_fast": [110.0] * n if bullish else [90.0] * n,
            "ema_slow": [100.0] * n,
            "adx_14": [25.0] * n,
            "atr_volatility": [0.02] * n,
            "volume_sma_ratio": [1.2] * n,
        })

    def test_filter_signals_empty_df(self):
        """Empty DataFrame passes through without error."""
        from pythia.adapters.ml_gate import MLMetaGate

        gate = MLMetaGate()
        result = gate.filter_signals(pd.DataFrame())
        assert result.empty

    def test_filter_signals_no_base_signals(self):
        """When no rows match base_mask, enter_long=0 everywhere."""
        from pythia.adapters.ml_gate import MLMetaGate

        gate = MLMetaGate()
        df = self._make_signal_df(bullish=False)
        result = gate.filter_signals(df)
        assert (result["enter_long"] == 0).all()
        assert (result["ml_confidence"] == 0.0).all()

    def test_filter_signals_with_bullish_data(self):
        """Bullish data produces enter_long and ml_confidence columns."""
        from pythia.adapters.ml_gate import MLMetaGate

        gate = MLMetaGate()
        df = self._make_signal_df(bullish=True)
        result = gate.filter_signals(df)
        assert "enter_long" in result.columns
        assert "ml_confidence" in result.columns
        # Some rows may be flagged depending on random mock probs
        assert result["enter_long"].dtype in [np.int64, np.int32, int]

    def test_filter_signals_missing_feature_cols(self):
        """Missing feature columns (adx_14 etc) auto-filled with 0.0."""
        from pythia.adapters.ml_gate import MLMetaGate

        gate = MLMetaGate()
        df = pd.DataFrame({
            "rsi": [50.0, 45.0],
            "ema_fast": [110.0, 112.0],
            "ema_slow": [100.0, 100.0],
        })
        result = gate.filter_signals(df)
        assert "adx_14" in result.columns
        assert "atr_volatility" in result.columns
        assert "volume_sma_ratio" in result.columns

    def test_filter_signals_inference_error_raises_ml_gate_error(self):
        """If predict_proba raises, MLGateError with AI_PREDICTION_FAILED code."""
        from pythia.adapters.ml_gate import MLMetaGate

        gate = MLMetaGate()
        gate.is_loaded = True
        gate.model = MagicMock()
        gate.model.predict_proba.side_effect = RuntimeError("CUDA OOM")

        df = self._make_signal_df(bullish=True)
        with pytest.raises(MLGateError) as exc_info:
            gate.filter_signals(df)

        assert exc_info.value.code == ErrorCode.AI_PREDICTION_FAILED
        assert "CUDA OOM" in exc_info.value.message

    def test_model_load_unexpected_error_raises(self):
        """Non-IO model load errors must propagate as MLGateError."""
        from pythia.adapters.ml_gate import MLMetaGate, XGBClassifier

        with patch.object(
            XGBClassifier, "load_model", side_effect=ValueError("corrupt weights")
        ):
            with pytest.raises(MLGateError) as exc_info:
                MLMetaGate(model_path="corrupt_model.json")

            assert exc_info.value.code == ErrorCode.AI_MODEL_NOT_LOADED
            assert "corrupt weights" in exc_info.value.message

    def test_threshold_default(self):
        """Default confidence threshold is 0.65."""
        from pythia.adapters.ml_gate import MLMetaGate

        gate = MLMetaGate()
        assert gate.threshold == 0.65


if __name__ == "__main__":
    unittest.main()
