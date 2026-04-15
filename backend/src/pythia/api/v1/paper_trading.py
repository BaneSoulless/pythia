"""Paper trading status and control endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from pythia.core.config import settings
from pythia.infrastructure.persistence.database import get_db
from pythia.infrastructure.trading_mode_router import (
    get_trading_mode,
    is_paper_mode,
)

router = APIRouter(prefix="/paper", tags=["paper-trading"])


@router.get("/status")
async def get_paper_status(db: Session = Depends(get_db)):
    """Returns current paper trading session summary and promotion eligibility."""
    from pythia.infrastructure.brokers.paper_trading_broker import PaperTradingBroker

    if not is_paper_mode():
        return {"mode": "live", "paper_active": False}

    broker = PaperTradingBroker(db_session=db)
    summary = broker.get_session_summary()

    settings_thresholds = {
        "min_trades": getattr(settings, "PAPER_MIN_TRADES_FOR_PROMOTE", 50),
        "min_sharpe": getattr(settings, "PAPER_SHARPE_THRESHOLD", 1.5),
        "max_drawdown": getattr(settings, "PAPER_DRAWDOWN_MAX", 0.15),
        "min_win_rate": getattr(settings, "PAPER_WIN_RATE_MIN", 0.45),
    }

    total_trades = summary.get("total_trades", 0)
    win_rate = summary.get("win_rate", 0)
    total_pnl = summary.get("total_pnl", 0)

    promote_checks = {
        "trades_ok": total_trades >= settings_thresholds["min_trades"],
        "win_rate_ok": win_rate >= settings_thresholds["min_win_rate"],
        "pnl_ok": total_pnl > 0,
    }
    promote_ready = all(promote_checks.values())

    return {
        "mode": get_trading_mode(),
        "paper_active": True,
        "session": summary,
        "thresholds": settings_thresholds,
        "promote_checks": promote_checks,
        "promote_ready": promote_ready,
        "next_action": (
            "promote_evolved_config() then set TRADING_MODE=live"
            if promote_ready
            else f"continue paper trading ({max(0, settings_thresholds['min_trades'] - total_trades)} trades remaining)"
        ),
    }


@router.get("/trades")
async def get_paper_trades(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Returns last N paper trades with PnL details."""
    from sqlalchemy import text

    rows = db.execute(
        text("""
            SELECT symbol, side, quantity, entry_price, exit_price,
                   pnl, pnl_pct, is_win, opened_at, closed_at,
                   evolved_config_used, evolved_node_id
            FROM paper_trades
            ORDER BY opened_at DESC LIMIT :lim
        """),
        {"lim": limit},
    ).fetchall()
    
    return {
        "count": len(rows),
        "trades": [dict(r._mapping) for r in rows],
    }
