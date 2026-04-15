"""PaperTradingBroker — wraps Alpaca paper-api.alpaca.markets.

Implements TradingPort interface identically to AlpacaAdapter.
Controlled by TRADING_MODE env var. Records all trades to
paper_trades table for ASI-Evolve shadow validation.

Architecture:
- Executes real orders on Alpaca paper endpoint (no simulated fills)
- Tracks PnL, win rate, and session stats in paper_sessions
- Promotion gate: 50 trades + win_rate>45% + positive PnL
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

import structlog
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest
from sqlalchemy import text
from sqlalchemy.orm import Session

from pythia.core.config import settings
from pythia.core.ports import TradingPort

logger = structlog.get_logger("PYTHIA-PAPER-BROKER")


class PaperTradingBroker(TradingPort):
    """Executes orders on Alpaca paper endpoint.

    Mirrors AlpacaAdapter's TradingPort interface so
    MultiAssetOrchestrator requires zero modification to switch modes.

    TradingPort methods implemented:
    - place_order(symbol, side, quantity, price) -> dict
    - get_positions() -> list[dict]
    - get_account_status() -> dict
    - is_market_open() -> bool
    """

    def __init__(self, db_session: Session) -> None:
        self.db = db_session
        self.session_id = str(uuid.uuid4())
        self.initial_capital = Decimal(
            str(getattr(settings, "PAPER_INITIAL_CAPITAL", 10000.0))
        )

        api_key = getattr(settings, "ALPACA_PAPER_API_KEY", "") or settings.ALPACA_API_KEY
        secret_key = getattr(settings, "ALPACA_PAPER_SECRET_KEY", "") or settings.ALPACA_SECRET_KEY

        self._client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=True,
        )
        self._ensure_session()
        logger.info(
            "paper_broker_initialized",
            session_id=self.session_id,
            capital=float(self.initial_capital),
        )

    # ── TradingPort interface ─────────────────────────────────

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float | None = None,
        signal_scores: Optional[dict] = None,
        evolved_node_id: Optional[str] = None,
    ) -> dict:
        """Place a market order on Alpaca paper endpoint.

        Matches TradingPort.place_order signature exactly for
        the required params. Extra params are paper-specific metadata.
        """
        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL,
            time_in_force=TimeInForce.GTC,
        )
        try:
            order = self._client.submit_order(order_data=order_request)
            fill_price = float(
                order.filled_avg_price or order.limit_price or price or 0
            )

            self._record_trade_open(
                symbol=symbol,
                side=side.upper(),
                qty=quantity,
                entry_price=fill_price,
                alpaca_order_id=str(order.id),
                signal_scores=signal_scores,
                evolved_node_id=evolved_node_id,
            )
            logger.info(
                "paper_order_placed",
                symbol=symbol,
                side=side,
                qty=quantity,
                fill_price=fill_price,
                order_id=str(order.id),
            )
            return {
                "id": str(order.id),
                "order_id": str(order.id),
                "fill_price": fill_price,
                "price": fill_price,
                "qty": quantity,
                "symbol": symbol,
                "side": side.upper(),
                "paper": True,
            }
        except Exception as exc:
            logger.error("paper_order_failed", symbol=symbol, error=str(exc))
            raise

    async def get_positions(self) -> list[dict]:
        """Fetch all open positions from Alpaca paper account."""
        try:
            positions = self._client.get_all_positions()
            return [dict(p) for p in positions]
        except Exception as exc:
            logger.error("paper_get_positions_failed", error=str(exc))
            raise

    async def get_account_status(self) -> dict:
        """Fetch paper account equity, buying power, and compliance."""
        try:
            account = self._client.get_account()
            return {
                "equity": float(account.equity),
                "buying_power": float(account.buying_power),
                "daytrade_count": int(account.daytrade_count),
                "pdt_status": account.pattern_day_trader,
            }
        except Exception as exc:
            logger.error("paper_get_account_failed", error=str(exc))
            raise

    async def is_market_open(self) -> bool:
        """Check if market is open via Alpaca clock API."""
        try:
            clock = self._client.get_clock()
            return clock.is_open
        except Exception:
            return True  # Fail-open for paper trading

    # ── Paper-specific methods ────────────────────────────────

    async def close_position(
        self,
        symbol: str,
        exit_price: float,
        order_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Close an open paper position. Calculates and records PnL."""
        row = self.db.execute(
            text("""
                SELECT id, entry_price, quantity, side
                FROM paper_trades
                WHERE symbol=:sym AND closed_at IS NULL AND session_id=:sid
                ORDER BY opened_at DESC LIMIT 1
            """),
            {"sym": symbol, "sid": self.session_id},
        ).fetchone()

        if not row:
            logger.warning("paper_close_no_open_position", symbol=symbol)
            return {"error": "no_open_position", "symbol": symbol}

        trade_id, entry_price, qty, side = row
        entry = Decimal(str(entry_price))
        exit_ = Decimal(str(exit_price))
        quantity = Decimal(str(qty))

        if side.upper() == "BUY":
            pnl = (exit_ - entry) * quantity
        else:
            pnl = (entry - exit_) * quantity

        pnl_pct = float(
            (pnl / (entry * quantity)) * 100
        ) if entry * quantity != 0 else 0.0
        is_win = pnl > 0

        self.db.execute(
            text("""
                UPDATE paper_trades
                SET exit_price=:ep, pnl=:pnl, pnl_pct=:pct,
                    is_win=:win, closed_at=:ts
                WHERE id=:tid
            """),
            {
                "ep": float(exit_),
                "pnl": float(pnl),
                "pct": pnl_pct,
                "win": is_win,
                "ts": datetime.now(timezone.utc),
                "tid": trade_id,
            },
        )
        self._update_session_stats(pnl=float(pnl), is_win=is_win)
        self.db.commit()

        logger.info(
            "paper_position_closed",
            symbol=symbol,
            pnl=float(pnl),
            pnl_pct=pnl_pct,
            win=is_win,
        )

        from pythia.infrastructure.monitoring.prometheus_exporter import get_metrics_exporter
        metrics = get_metrics_exporter()
        metrics.record_paper_trade(symbol, side.upper(), is_win)

        summary = self.get_session_summary()
        metrics.update_paper_session(
            pnl=summary.get("total_pnl", 0.0),
            win_rate=summary.get("win_rate", 0.0),
            eligible=summary.get("promote_eligible", False)
        )

        return {
            "trade_id": trade_id,
            "symbol": symbol,
            "pnl": float(pnl),
            "pnl_pct": pnl_pct,
            "is_win": is_win,
            "paper": True,
        }

    def get_session_summary(self) -> dict[str, Any]:
        """Return current paper session metrics."""
        row = self.db.execute(
            text("""
                SELECT total_trades, win_trades, total_pnl,
                       current_capital, initial_capital,
                       sharpe_ratio, max_drawdown, promote_eligible
                FROM paper_sessions WHERE id=:sid
            """),
            {"sid": self.session_id},
        ).fetchone()
        if not row:
            return {}
        t, w, pnl, curr, init, sharpe, dd, eligible = row
        win_rate = (w / t) if t and t > 0 else 0.0
        return {
            "session_id": self.session_id,
            "total_trades": t or 0,
            "win_rate": round(win_rate, 4),
            "total_pnl": float(pnl or 0),
            "current_capital": float(curr or 0),
            "initial_capital": float(init or 0),
            "return_pct": round(
                ((float(curr or 0) - float(init or 1)) / float(init or 1)) * 100, 2
            ),
            "sharpe_ratio": float(sharpe) if sharpe else None,
            "max_drawdown": float(dd) if dd else None,
            "promote_eligible": bool(eligible),
        }

    # ── Internal helpers ──────────────────────────────────────

    def _ensure_session(self) -> None:
        """Create or recover the active paper session in DB."""
        existing = self.db.execute(
            text("SELECT id FROM paper_sessions WHERE status='active' LIMIT 1")
        ).fetchone()
        if existing:
            self.session_id = existing[0]
            return

        self.db.execute(
            text("""
                INSERT INTO paper_sessions
                  (id, started_at, initial_capital, current_capital,
                   total_trades, win_trades, total_pnl, status)
                VALUES
                  (:id, :ts, :cap, :cap, 0, 0, 0, 'active')
            """),
            {
                "id": self.session_id,
                "ts": datetime.now(timezone.utc),
                "cap": float(self.initial_capital),
            },
        )
        self.db.commit()

    def _record_trade_open(
        self,
        symbol: str,
        side: str,
        qty: float,
        entry_price: float,
        alpaca_order_id: str,
        signal_scores: Optional[dict],
        evolved_node_id: Optional[str],
    ) -> None:
        """Insert open trade record into paper_trades."""
        self.db.execute(
            text("""
                INSERT INTO paper_trades
                  (symbol, side, quantity, entry_price, opened_at,
                   alpaca_order_id, signal_scores, evolved_config_used,
                   evolved_node_id, session_id)
                VALUES
                  (:sym, :side, :qty, :ep, :ts, :oid, :scores,
                   :evo, :nid, :sid)
            """),
            {
                "sym": symbol,
                "side": side,
                "qty": qty,
                "ep": entry_price,
                "ts": datetime.now(timezone.utc),
                "oid": alpaca_order_id,
                "scores": json.dumps(signal_scores) if signal_scores else None,
                "evo": evolved_node_id is not None,
                "nid": evolved_node_id,
                "sid": self.session_id,
            },
        )
        self.db.commit()

    def _update_session_stats(self, pnl: float, is_win: bool) -> None:
        """Increment session counters after trade close."""
        self.db.execute(
            text("""
                UPDATE paper_sessions
                SET total_trades = total_trades + 1,
                    win_trades = win_trades + :win_inc,
                    total_pnl = total_pnl + :pnl,
                    current_capital = current_capital + :pnl
                WHERE id = :sid
            """),
            {
                "win_inc": 1 if is_win else 0,
                "pnl": pnl,
                "sid": self.session_id,
            },
        )
