"""Tests for AssetClass inference and per-class Kelly/Sharpe config."""
from __future__ import annotations
import math
import pytest
from pythia.core.asset_class import (
    AssetClass,
    infer_asset_class,
    get_asset_class_config,
    kelly_for_prediction_market,
    ASSET_CLASS_CONFIGS,
)


class TestAssetClassInference:
    def test_btcusd_is_crypto(self):
        assert infer_asset_class("BTC/USD") == AssetClass.CRYPTO

    def test_ethusdt_is_crypto(self):
        assert infer_asset_class("ETHUSDT") == AssetClass.CRYPTO

    def test_aapl_is_stock(self):
        assert infer_asset_class("AAPL") == AssetClass.STOCK

    def test_spy_is_stock(self):
        assert infer_asset_class("SPY") == AssetClass.STOCK

    def test_tsla_is_stock(self):
        assert infer_asset_class("TSLA") == AssetClass.STOCK

    def test_pm_prefix_is_prediction_market(self):
        assert infer_asset_class("PM:TRUMP-WIN-2028") == AssetClass.PREDICTION_MARKET

    def test_poly_prefix_is_prediction_market(self):
        assert infer_asset_class("POLY:BTC-100K-2026") == AssetClass.PREDICTION_MARKET

    def test_kal_prefix_is_prediction_market(self):
        assert infer_asset_class("KAL:FED-RATE-CUT-2026") == AssetClass.PREDICTION_MARKET

    def test_lowercase_symbol_still_works(self):
        assert infer_asset_class("aapl") == AssetClass.STOCK

    def test_btc_without_slash_is_crypto(self):
        assert infer_asset_class("BTCUSDT") == AssetClass.CRYPTO


class TestAssetClassConfigs:
    def test_crypto_sharpe_factor_correct(self):
        cfg = get_asset_class_config(AssetClass.CRYPTO)
        expected = math.sqrt(8 * 365)
        assert cfg.sharpe_annualization_factor == pytest.approx(expected, abs=0.01)

    def test_stock_sharpe_factor_correct(self):
        cfg = get_asset_class_config(AssetClass.STOCK)
        expected = math.sqrt(2 * 252)
        assert cfg.sharpe_annualization_factor == pytest.approx(expected, abs=0.01)

    def test_pm_sharpe_factor_correct(self):
        cfg = get_asset_class_config(AssetClass.PREDICTION_MARKET)
        expected = math.sqrt(60)
        assert cfg.sharpe_annualization_factor == pytest.approx(expected, abs=0.01)

    def test_stock_fractional_false(self):
        cfg = get_asset_class_config(AssetClass.STOCK)
        assert cfg.fractional_qty is False

    def test_crypto_fractional_true(self):
        cfg = get_asset_class_config(AssetClass.CRYPTO)
        assert cfg.fractional_qty is True

    def test_pm_fractional_false(self):
        cfg = get_asset_class_config(AssetClass.PREDICTION_MARKET)
        assert cfg.fractional_qty is False

    def test_all_configs_kelly_max_in_range(self):
        for ac, cfg in ASSET_CLASS_CONFIGS.items():
            assert 0 < cfg.kelly_max_pct <= 1.0, \
                f"{ac}: kelly_max_pct={cfg.kelly_max_pct} out of range"

    def test_all_configs_kelly_floor_positive(self):
        for ac, cfg in ASSET_CLASS_CONFIGS.items():
            assert cfg.kelly_floor_pct > 0, \
                f"{ac}: kelly_floor_pct must be positive"

    def test_pm_kelly_max_higher_than_stock(self):
        pm = get_asset_class_config(AssetClass.PREDICTION_MARKET)
        stock = get_asset_class_config(AssetClass.STOCK)
        # Prediction market usually allows higher Kelly cap in our logic
        assert pm.kelly_max_pct > stock.kelly_max_pct

    def test_crypto_preservation_threshold(self):
        cfg = get_asset_class_config(AssetClass.CRYPTO)
        assert cfg.capital_preservation_threshold == pytest.approx(-0.10, abs=0.001)

    def test_stock_preservation_more_conservative(self):
        stock = get_asset_class_config(AssetClass.STOCK)
        crypto = get_asset_class_config(AssetClass.CRYPTO)
        # Stock preservation kicks in earlier (less negative = more conservative)
        assert stock.capital_preservation_threshold > crypto.capital_preservation_threshold


class TestPMKellyFormula:
    def test_pm_kelly_positive_edge(self):
        # Modello: 60%, mercato prezza 40% → edge netto
        k = kelly_for_prediction_market(
            model_probability=0.60,
            market_odds_payout=1.5,
        )
        assert k > 0

    def test_pm_kelly_no_edge_zero(self):
        # model_prob = market_implied_prob → edge = 0
        k = kelly_for_prediction_market(
            model_probability=0.40,
            market_odds_payout=1.5,
        )
        # 0.40 - (1-0.40)/1.5 = 0.40 - 0.40 = 0.0
        assert k == pytest.approx(0.0, abs=0.001)

    def test_pm_kelly_zero_payout_returns_zero(self):
        k = kelly_for_prediction_market(
            model_probability=0.6,
            market_odds_payout=0.0,
        )
        assert k == 0.0

    def test_pm_kelly_negative_edge_returns_zero(self):
        # Modello < mercato → non scommettere
        k = kelly_for_prediction_market(
            model_probability=0.30,
            market_odds_payout=1.5,
        )
        assert k == 0.0

    def test_pm_kelly_high_confidence(self):
        # 80% prob, mercato a 50% → ottima opportunità
        k = kelly_for_prediction_market(
            model_probability=0.80,
            market_odds_payout=1.0,
        )
        assert k > 0.30  # edge molto alto → Kelly alto
