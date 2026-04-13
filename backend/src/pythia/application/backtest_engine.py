"""
Backtesting Engine — Pydantic V2 Migration
SOTA 2026

Architectural why:
- BacktestTrade and BacktestResults are now pydantic.BaseModel instead of
  @dataclass. This enforces schema validation at construction time (no silent
  type coercion from raw float arithmetic), enables JSON serialisation via
  .model_dump() / .model_dump_json(), and integrates with the Pydantic V2
  ecosystem already used throughout the rest of the pythia domain layer.
- Decimal precision is enforced for balance and position arithmetic to prevent
  float-drift compounding across multi-step replay sequences.
- BacktestEngine state uses typed annotations; the positions dict is now
  Dict[str, Decimal] to avoid silent float accumulation.
"""

import logging
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


class BacktestTrade(BaseModel):
    """Immutable record of a single trade executed during backtesting."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    commission: Decimal = Decimal("0.0")

    @field_validator("side")
    @classmethod
    def _valid_side(cls, v: str) -> str:
        v = v.lower()
        if v not in {"buy", "sell"}:
            raise ValueError(f"side must be 'buy' or 'sell', got: {v}")
        return v

    @field_validator("quantity", "price", "commission", mode="before")
    @classmethod
    def _coerce_decimal(cls, v: object) -> Decimal:
        return Decimal(str(v))

    @property
    def total_cost(self) -> Decimal:
        """Gross cost including commission."""
        return (self.quantity * self.price + self.commission).quantize(
            Decimal("0.0001"), ROUND_HALF_UP
        )


class BacktestResults(BaseModel):
    """Aggregated performance metrics from a completed backtest run."""

    model_config = ConfigDict(frozen=True)

    initial_balance: Decimal
    final_balance: Decimal
    total_return: Decimal
    total_return_pct: Decimal
    num_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    max_drawdown: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal = Decimal("0.0")
    calmar_ratio: Decimal = Decimal("0.0")
    trades: list[BacktestTrade] = Field(default_factory=list)
    equity_curve: list[tuple[datetime, Decimal]] = Field(default_factory=list)

    @field_validator(
        "initial_balance", "final_balance", "total_return", "total_return_pct",
        "win_rate", "max_drawdown", "sharpe_ratio", "sortino_ratio", "calmar_ratio",
        mode="before",
    )
    @classmethod
    def _coerce_decimal(cls, v: object) -> Decimal:
        return Decimal(str(v))

    def to_dict(self) -> dict:
        return {
            "initial_balance": float(self.initial_balance),
            "final_balance": float(self.final_balance),
            "total_return": float(self.total_return),
            "total_return_pct": float(self.total_return_pct),
            "num_trades": self.num_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": float(self.win_rate),
            "max_drawdown": float(self.max_drawdown),
            "sharpe_ratio": float(self.sharpe_ratio),
            "sortino_ratio": float(self.sortino_ratio),
            "calmar_ratio": float(self.calmar_ratio),
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class BacktestEngine:
    """
    Backtesting engine for trading strategies.

    Maintains state as typed Decimal maps to prevent float-drift accumulation
    in multi-step compounding. Position sizing and P&L are Decimal-precise
    throughout.
    """

    def __init__(
        self,
        initial_balance: float = 10_000.0,
        commission_rate: float = 0.001,
        min_balance: float = 10.0,
    ) -> None:
        self.initial_balance: Decimal = Decimal(str(initial_balance))
        self.commission_rate: Decimal = Decimal(str(commission_rate))
        self.min_balance: Decimal = Decimal(str(min_balance))
        self.balance: Decimal = self.initial_balance
        self.positions: dict[str, Decimal] = {}
        self.trades: list[BacktestTrade] = []
        self.equity_curve: list[tuple[datetime, Decimal]] = []

    def reset(self) -> None:
        """Reset engine state for a fresh backtest run."""
        self.balance = self.initial_balance
        self.positions = {}
        self.trades = []
        self.equity_curve = []

    def execute_buy(
        self, timestamp: datetime, symbol: str, quantity: float, price: float
    ) -> bool:
        """Execute a buy order; returns False if balance is insufficient."""
        qty = Decimal(str(quantity))
        px = Decimal(str(price))
        commission = (px * qty * self.commission_rate).quantize(Decimal("0.0001"), ROUND_HALF_UP)
        total_cost = px * qty + commission
        if self.balance - total_cost < self.min_balance:
            return False
        self.balance -= total_cost
        self.positions[symbol] = self.positions.get(symbol, Decimal("0")) + qty
        self.trades.append(
            BacktestTrade(
                timestamp=timestamp,
                symbol=symbol,
                side="buy",
                quantity=qty,
                price=px,
                commission=commission,
            )
        )
        return True

    def execute_sell(
        self, timestamp: datetime, symbol: str, quantity: float, price: float
    ) -> bool:
        """Execute a sell order; returns False if position is insufficient."""
        qty = Decimal(str(quantity))
        px = Decimal(str(price))
        held = self.positions.get(symbol, Decimal("0"))
        if held < qty:
            return False
        commission = (px * qty * self.commission_rate).quantize(Decimal("0.0001"), ROUND_HALF_UP)
        proceeds = px * qty - commission
        self.balance += proceeds
        self.positions[symbol] = held - qty
        if self.positions[symbol] <= Decimal("0"):
            del self.positions[symbol]
        self.trades.append(
            BacktestTrade(
                timestamp=timestamp,
                symbol=symbol,
                side="sell",
                quantity=qty,
                price=px,
                commission=commission,
            )
        )
        return True

    def record_equity(
        self, timestamp: datetime, current_prices: dict[str, float]
    ) -> None:
        """Snapshot portfolio value and append to equity curve."""
        prices = {sym: Decimal(str(px)) for sym, px in current_prices.items()}
        positions_value = sum(
            qty * prices.get(sym, Decimal("0"))
            for sym, qty in self.positions.items()
        )
        self.equity_curve.append((timestamp, self.balance + positions_value))

    def calculate_metrics(self) -> BacktestResults:
        """Compute full performance metrics including Sortino and Calmar ratios."""
        final_balance = (
            self.equity_curve[-1][1] if self.equity_curve else self.balance
        )
        total_return = final_balance - self.initial_balance
        total_return_pct = (
            total_return / self.initial_balance * Decimal("100")
        ) if self.initial_balance else Decimal("0")

        winning_trades = 0
        losing_trades = 0
        buy_queue: dict[str, list[BacktestTrade]] = {}

        for trade in self.trades:
            if trade.side == "buy":
                buy_queue.setdefault(trade.symbol, []).append(trade)
            elif trade.side == "sell" and buy_queue.get(trade.symbol):
                buy_trade = buy_queue[trade.symbol].pop(0)
                pnl = (
                    (trade.price - buy_trade.price) * trade.quantity
                    - trade.commission
                    - buy_trade.commission
                )
                if pnl > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1

        total_closed = winning_trades + losing_trades
        win_rate = (
            Decimal(str(winning_trades)) / Decimal(str(total_closed)) * Decimal("100")
            if total_closed > 0
            else Decimal("0")
        )

        max_drawdown = self._calculate_max_drawdown()
        sharpe = self._calculate_sharpe_ratio()
        sortino = self._calculate_sortino_ratio()
        calmar = self._calculate_calmar_ratio(total_return_pct, max_drawdown)

        return BacktestResults(
            initial_balance=self.initial_balance,
            final_balance=final_balance,
            total_return=total_return,
            total_return_pct=total_return_pct,
            num_trades=len(self.trades),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            trades=list(self.trades),
            equity_curve=list(self.equity_curve),
        )

    # ------------------------------------------------------------------
    # Private metric calculators
    # ------------------------------------------------------------------

    def _get_returns(self) -> list[float]:
        if len(self.equity_curve) < 2:
            return []
        return [
            float(self.equity_curve[i][1] - self.equity_curve[i - 1][1])
            / float(self.equity_curve[i - 1][1])
            for i in range(1, len(self.equity_curve))
        ]

    def _calculate_max_drawdown(self) -> Decimal:
        """Maximum drawdown as a percentage of peak equity."""
        if not self.equity_curve:
            return Decimal("0.0")
        values = [float(v) for _, v in self.equity_curve]
        peak = values[0]
        max_dd = 0.0
        for value in values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak else 0.0
            if dd > max_dd:
                max_dd = dd
        return Decimal(str(max_dd * 100))

    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> Decimal:
        """Annualised Sharpe ratio (252-day convention)."""
        returns = self._get_returns()
        if not returns:
            return Decimal("0.0")
        arr = np.array(returns, dtype=float)
        std = float(np.std(arr))
        if std == 0:
            return Decimal("0.0")
        sharpe = (float(np.mean(arr)) - risk_free_rate / 252) / std * np.sqrt(252)
        return Decimal(str(round(sharpe, 4)))

    def _calculate_sortino_ratio(self, risk_free_rate: float = 0.02) -> Decimal:
        """Sortino ratio — penalises only downside volatility."""
        returns = self._get_returns()
        if not returns:
            return Decimal("0.0")
        arr = np.array(returns, dtype=float)
        downside = arr[arr < 0]
        downside_std = float(np.std(downside)) if len(downside) > 1 else 0.0
        if downside_std == 0:
            return Decimal("0.0")
        sortino = (float(np.mean(arr)) - risk_free_rate / 252) / downside_std * np.sqrt(252)
        return Decimal(str(round(sortino, 4)))

    def _calculate_calmar_ratio(
        self, total_return_pct: Decimal, max_drawdown: Decimal
    ) -> Decimal:
        """Calmar ratio — annualised return divided by max drawdown."""
        if max_drawdown == 0:
            return Decimal("0.0")
        return (total_return_pct / max_drawdown).quantize(Decimal("0.0001"), ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Public utility
# ---------------------------------------------------------------------------


def run_strategy_backtest(
    strategy_func,
    historical_data: pd.DataFrame,
    initial_balance: float = 10_000.0,
    **strategy_params,
) -> BacktestResults:
    """
    Execute a backtest with the supplied strategy callable.

    Args:
        strategy_func:   Callable(engine, historical_data, **params).
        historical_data: DataFrame with columns: timestamp, symbol, open,
                         high, low, close, volume.
        initial_balance: Starting cash balance.
        **strategy_params: Forwarded verbatim to strategy_func.

    Returns:
        BacktestResults (Pydantic V2 model, JSON-serialisable).
    """
    engine = BacktestEngine(initial_balance=initial_balance)
    strategy_func(engine, historical_data, **strategy_params)
    return engine.calculate_metrics()
