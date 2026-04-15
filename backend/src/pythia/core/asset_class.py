"""
Asset class definitions and per-class configuration for Pythia.
Controls Kelly sizing, Sharpe annualization, qty rounding, and broker routing.
"""
from __future__ import annotations

import math
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class AssetClass(str, Enum):
    CRYPTO = "CRYPTO"
    STOCK = "STOCK"
    PREDICTION_MARKET = "PREDICTION_MARKET"


@dataclass(frozen=True)
class AssetClassConfig:
    name: AssetClass
    sharpe_annualization_factor: float
    kelly_max_pct: float
    kelly_floor_pct: float
    slippage_est: float
    capital_preservation_threshold: float  # monthly drawdown trigger
    fractional_qty: bool
    broker_type: str  # "alpaca" | "polymarket" | "kalshi"
    trading_days_per_year: int


ASSET_CLASS_CONFIGS: dict[AssetClass, AssetClassConfig] = {
    AssetClass.CRYPTO: AssetClassConfig(
        name=AssetClass.CRYPTO,
        sharpe_annualization_factor=math.sqrt(8 * 365),  # 54.06
        kelly_max_pct=0.15,
        kelly_floor_pct=0.005,
        slippage_est=0.001,
        capital_preservation_threshold=-0.10,
        fractional_qty=True,
        broker_type="alpaca",
        trading_days_per_year=365,
    ),
    AssetClass.STOCK: AssetClassConfig(
        name=AssetClass.STOCK,
        sharpe_annualization_factor=math.sqrt(2 * 252),  # 22.45
        kelly_max_pct=0.10,
        kelly_floor_pct=0.005,
        slippage_est=0.0005,
        capital_preservation_threshold=-0.07,
        fractional_qty=False,  # default intero, True se Alpaca fractional
        broker_type="alpaca",
        trading_days_per_year=252,
    ),
    AssetClass.PREDICTION_MARKET: AssetClassConfig(
        name=AssetClass.PREDICTION_MARKET,
        sharpe_annualization_factor=math.sqrt(60),  # 7.75
        kelly_max_pct=0.25,
        kelly_floor_pct=0.01,
        slippage_est=0.0,
        capital_preservation_threshold=-0.12,
        fractional_qty=False,
        broker_type="polymarket",  # o "kalshi"
        trading_days_per_year=365,  # eventi 24/7
    ),
}


def get_asset_class_config(asset_class: AssetClass) -> AssetClassConfig:
    return ASSET_CLASS_CONFIGS[asset_class]


def infer_asset_class(symbol: str) -> AssetClass:
    """
    Inferisce l'asset class dal simbolo.
    Regole:
    - crypto: contiene "/", "USD", "USDT", "BTC", "ETH" ecc.
    - prediction market: prefisso "PM:" o dominio .poly / .kal
    - stock: tutto il resto (AAPL, TSLA, SPY...)
    """
    sym = symbol.upper().strip()

    # Prediction market markers
    if sym.startswith("PM:") or sym.startswith("POLY:") or sym.startswith("KAL:"):
        return AssetClass.PREDICTION_MARKET

    # Crypto markers
    crypto_markers = {
        "/", "BTC", "ETH", "SOL", "BNB", "USDT", "USDC",
        "XRP", "ADA", "DOGE", "MATIC", "AVAX", "DOT",
    }
    if any(m in sym for m in crypto_markers):
        return AssetClass.CRYPTO

    # Default: stock
    return AssetClass.STOCK


def kelly_for_prediction_market(
    model_probability: float,
    market_odds_payout: float,
) -> float:
    """
    Kelly ottimale per Prediction Market.
    f* = p - (1-p) / b
    dove:
      p = probabilità stimata dal modello (0-1)
      b = payout netto se vince (es. compra a 0.40, vince → b = 0.60/0.40 = 1.5)
    """
    if market_odds_payout <= 0 or model_probability <= 0:
        return 0.0
    kelly = model_probability - (1 - model_probability) / market_odds_payout
    return max(kelly, 0.0)
