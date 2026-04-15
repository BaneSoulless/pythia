"""Tests for MonthlyTargetTracker and Kelly position sizing."""
import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal


class TestKellyCalculation:
    def test_kelly_positive_edge(self):
        from pythia.application.monthly_target_tracker import MonthlyTargetTracker
        kelly = MonthlyTargetTracker._calculate_kelly(
            win_rate=0.55, avg_win_loss_ratio=1.3
        )
        assert kelly > 0
        assert kelly < 1.0

    def test_kelly_negative_edge_returns_floor(self):
        from pythia.application.monthly_target_tracker import MonthlyTargetTracker
        kelly = MonthlyTargetTracker._calculate_kelly(
            win_rate=0.30, avg_win_loss_ratio=0.8
        )
        assert kelly == 0.0

    def test_kelly_zero_ratio_returns_floor(self):
        from pythia.application.monthly_target_tracker import MonthlyTargetTracker
        kelly = MonthlyTargetTracker._calculate_kelly(
            win_rate=0.5, avg_win_loss_ratio=0.0
        )
        assert kelly == pytest.approx(0.005, abs=0.001)


class TestMonthlyStatusLogic:
    def _make_tracker(self):
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None
        with patch("pythia.application.monthly_target_tracker.MonthlyTargetTracker._ensure_month_record"):
            from pythia.application.monthly_target_tracker import MonthlyTargetTracker
            from pythia.core.asset_class import AssetClass, get_asset_class_config
            t = MonthlyTargetTracker.__new__(MonthlyTargetTracker)
            t.db = db
            t.initial_capital = Decimal("10000")
            t.is_paper = True
            t.year_month = "2026-04"
            t.asset_class = AssetClass.CRYPTO
            t.asset_cfg = get_asset_class_config(AssetClass.CRYPTO)
            return t

    def test_status_ahead_when_return_exceeds_target(self):
        tracker = self._make_tracker()
        tracker.db.execute.return_value.fetchone.return_value = None
        result = tracker.update_after_trade(
            current_capital=11100.0,  # +11%
            trade_count=60,
            win_rate=0.55,
            avg_win_loss_ratio=1.3,
        )
        assert result["status"] == "ahead"
        assert result["sizing_mode"] == "reduced_kelly"

    def test_status_behind_reduces_kelly_factor(self):
        tracker = self._make_tracker()
        result = tracker.update_after_trade(
            current_capital=10200.0,  # +2%, run-rate basso
            trade_count=25,
            win_rate=0.48,
            avg_win_loss_ratio=1.1,
        )
        assert result["status"] in ("behind", "on_track")
        assert result["kelly_factor"] <= 0.15

    def test_capital_preservation_blocks_trades(self):
        tracker = self._make_tracker()
        result = tracker.update_after_trade(
            current_capital=8900.0,  # -11% → preservation
            trade_count=30,
            win_rate=0.30,
            avg_win_loss_ratio=0.7,
        )
        assert result["status"] == "capital_preservation"
        assert result["kelly_factor"] == pytest.approx(0.005, abs=0.001)

    def test_kelly_hard_cap_15pct(self):
        tracker = self._make_tracker()
        result = tracker.update_after_trade(
            current_capital=10050.0,
            trade_count=10,
            win_rate=0.90,      # win rate estremo
            avg_win_loss_ratio=5.0,  # ratio estremo
        )
        assert result["kelly_factor"] <= 0.15

    def test_kelly_floor_05pct(self):
        tracker = self._make_tracker()
        result = tracker.update_after_trade(
            current_capital=10050.0,
            trade_count=10,
            win_rate=0.35,
            avg_win_loss_ratio=0.9,
        )
        assert result["kelly_factor"] >= 0.005


class TestSharpeCalculationWithAssetClass:
    """Tests _calculate_sharpe() with asset-class-specific annualization."""

    def _make_tracker_with_ac(self, asset_class):
        from unittest.mock import MagicMock, patch
        from decimal import Decimal
        db = MagicMock()
        # Mock paper_sessions query (per _calculate_sharpe)
        db.execute.return_value.scalar.return_value = "mock-session-id"
        # Mock paper_trades pnl_pct rows
        db.execute.return_value.fetchall.return_value = [
            (1.5,), (2.0,), (-0.5,), (1.0,), (0.8,),
        ]
        with patch(
            "pythia.application.monthly_target_tracker"
            ".MonthlyTargetTracker._ensure_month_record"
        ):
            from pythia.application.monthly_target_tracker import MonthlyTargetTracker
            from pythia.core.asset_class import AssetClass
            t = MonthlyTargetTracker.__new__(MonthlyTargetTracker)
            t.db = db
            t.initial_capital = Decimal("10000")
            t.is_paper = True
            t.year_month = "2026-04"
            t.asset_class = asset_class
            from pythia.core.asset_class import get_asset_class_config
            t.asset_cfg = get_asset_class_config(asset_class)
            return t

    def test_crypto_sharpe_higher_annualization(self):
        from pythia.core.asset_class import AssetClass
        crypto_tracker = self._make_tracker_with_ac(AssetClass.CRYPTO)
        stock_tracker = self._make_tracker_with_ac(AssetClass.STOCK)
        s_crypto = crypto_tracker._calculate_sharpe()
        s_stock = stock_tracker._calculate_sharpe()
        # Crypto ha factor più alto → Sharpe più alto a parità di PnL
        if s_crypto is not None and s_stock is not None:
            assert s_crypto > s_stock

    def test_sharpe_returns_none_on_single_trade(self):
        from pythia.core.asset_class import AssetClass
        tracker = self._make_tracker_with_ac(AssetClass.CRYPTO)
        tracker.db.execute.return_value.fetchall.return_value = [(1.5,)]
        result = tracker._calculate_sharpe()
        assert result is None

    def test_sharpe_returns_none_on_no_trades(self):
        from pythia.core.asset_class import AssetClass
        tracker = self._make_tracker_with_ac(AssetClass.CRYPTO)
        tracker.db.execute.return_value.fetchall.return_value = []
        result = tracker._calculate_sharpe()
        assert result is None

    def test_pm_sharpe_uses_correct_factor(self):
        import math
        from pythia.core.asset_class import AssetClass, get_asset_class_config
        tracker = self._make_tracker_with_ac(AssetClass.PREDICTION_MARKET)
        cfg = get_asset_class_config(AssetClass.PREDICTION_MARKET)
        assert cfg.sharpe_annualization_factor == pytest.approx(math.sqrt(60), abs=0.01)
        # _calculate_sharpe deve usare quel factor — non sollevare eccezioni
        result = tracker._calculate_sharpe()
        # Non importa il valore esatto, non deve essere None con 5 trade
        assert result is not None
