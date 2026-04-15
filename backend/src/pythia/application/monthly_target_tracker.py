"""
MonthlyTargetTracker: tracks progress toward +10%/month target.
Adjusts Kelly position sizing based on monthly run-rate.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

import structlog
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = structlog.get_logger("PYTHIA-MONTHLY-TARGET")

SizingMode = Literal["half_kelly", "reduced_kelly", "aggressive_kelly", "floor"]

TARGET_MONTHLY_RETURN = 0.10   # 10%
KELLY_BASE_FACTOR = 0.5        # half-Kelly default
KELLY_BEHIND_FACTOR = 0.60     # leggermente più aggressivo se in ritardo
KELLY_AHEAD_FACTOR = 0.30      # conservativo se in vantaggio
KELLY_MAX_PCT = 0.15           # mai più del 15% del capitale per trade
KELLY_FLOOR_PCT = 0.005        # mai meno dello 0.5%
DRAWDOWN_PRESERVATION_THRESHOLD = -0.10  # -10% mensile → capital preservation


from pythia.core.asset_class import AssetClass, get_asset_class_config

class MonthlyTargetTracker:
    def __init__(
        self,
        db: Session,
        initial_capital: float,
        is_paper: bool = True,
        asset_class: AssetClass = AssetClass.CRYPTO,
    ) -> None:
        self.db = db
        self.initial_capital = Decimal(str(initial_capital))
        self.is_paper = is_paper
        self.asset_class = asset_class
        self.asset_cfg = get_asset_class_config(asset_class)
        self.year_month = datetime.now(timezone.utc).strftime("%Y-%m")
        self._ensure_month_record()

    def _ensure_month_record(self) -> None:
        """Crea il record mensile se non esiste."""
        existing = self.db.execute(
            text("""
                SELECT id FROM monthly_target_log
                WHERE year_month=:ym AND is_paper=:ip
            """),
            {"ym": self.year_month, "ip": self.is_paper},
        ).fetchone()
        if not existing:
            self.db.execute(
                text("""
                    INSERT INTO monthly_target_log
                      (year_month, initial_capital, current_capital,
                       target_return_pct, status, is_paper, last_updated)
                    VALUES (:ym, :cap, :cap, :target, 'on_track', :ip, :ts)
                """),
                {
                    "ym": self.year_month,
                    "cap": float(self.initial_capital),
                    "target": TARGET_MONTHLY_RETURN,
                    "ip": self.is_paper,
                    "ts": datetime.now(timezone.utc),
                },
            )
            self.db.commit()
            logger.info(
                "monthly_target_record_created",
                year_month=self.year_month,
                target=TARGET_MONTHLY_RETURN,
                capital=float(self.initial_capital),
            )

    def _calculate_sharpe(
        self,
        symbol_filter: Optional[str] = None,
    ) -> Optional[float]:
        """
        Calcola Sharpe ratio annualizzato usando pnl_pct dalla
        paper_trades table per il mese corrente e asset class corrente.

        Usa risk-free rate 2% annuo da backtest_engine.py convention.
        Annualizzazione: self.asset_cfg.sharpe_annualization_factor

        Restituisce None se meno di 2 trade chiusi.
        """
        import math as _math
        from sqlalchemy import text

        # Costruisci query con filtro opzionale su symbol
        query = """
            SELECT pnl_pct FROM paper_trades
            WHERE session_id = :sid
              AND closed_at IS NOT NULL
              AND pnl_pct IS NOT NULL
        """
        params: dict = {"sid": self.db.execute(
            text("""
                SELECT id FROM paper_sessions
                WHERE status='active'
                ORDER BY started_at DESC LIMIT 1
            """)
        ).scalar()}

        if params[list(params.keys())[0]] is None:
            return None

        if symbol_filter:
            query += " AND symbol = :sym"
            params["sym"] = symbol_filter

        rows = self.db.execute(text(query), params).fetchall()
        pnl_pcts = [float(r[0]) / 100.0 for r in rows]  # converti % → ratio

        n = len(pnl_pcts)
        if n < 2:
            return None

        mean_r = sum(pnl_pcts) / n
        variance = sum((r - mean_r) ** 2 for r in pnl_pcts) / (n - 1)
        std_r = _math.sqrt(variance) if variance > 0 else 0.0

        if std_r == 0.0:
            return None

        # Risk-free rate per-trade (2% annuo / trading_days / trades_per_day)
        # Stima conservativa: 1 trade per trading day
        rf_per_trade = 0.02 / self.asset_cfg.trading_days_per_year
        excess_return = mean_r - rf_per_trade

        # Sharpe annualizzato
        sharpe = (excess_return / std_r) * self.asset_cfg.sharpe_annualization_factor
        return round(sharpe, 4)

    def update_after_trade(
        self,
        current_capital: float,
        trade_count: int,
        win_rate: float,
        avg_win_loss_ratio: float,
    ) -> dict:
        """
        Aggiorna il tracker dopo ogni trade chiuso.
        Ricalcola kelly_factor e sizing_mode.
        Restituisce il sizing da usare per il trade successivo.
        """
        now = datetime.now(timezone.utc)
        # Giorni trascorsi nel mese
        days_elapsed = now.day
        days_in_month = 30  # approssimazione
        days_remaining = max(days_in_month - days_elapsed, 1)

        current = Decimal(str(current_capital))
        initial = self.initial_capital
        actual_return = float((current - initial) / initial)

        # Run rate: se continuasse a questo ritmo, quanto guadagna a fine mese?
        run_rate = (actual_return / days_elapsed) * days_in_month
        target_progress = actual_return / TARGET_MONTHLY_RETURN  # 0.0 → 1.0

        # Determina status
        if actual_return <= self.asset_cfg.capital_preservation_threshold:
            status = "capital_preservation"
        elif target_progress >= 1.0:
            status = "ahead"
        elif run_rate >= TARGET_MONTHLY_RETURN * 0.80:
            status = "on_track"
        else:
            status = "behind"

        # Calcola Kelly
        kelly_raw = self._calculate_kelly(
            win_rate=win_rate,
            avg_win_loss_ratio=avg_win_loss_ratio,
        )

        # Adatta il fattore Kelly al status mensile
        if status == "capital_preservation":
            kelly_factor = 0.0  # nessun nuovo trade
            sizing_mode: SizingMode = "floor"
        elif status == "ahead":
            kelly_factor = kelly_raw * KELLY_AHEAD_FACTOR
            sizing_mode = "reduced_kelly"
        elif status == "behind":
            kelly_factor = kelly_raw * KELLY_BEHIND_FACTOR
            sizing_mode = "aggressive_kelly"
        else:
            kelly_factor = kelly_raw * KELLY_BASE_FACTOR
            sizing_mode = "half_kelly"

        # Hard caps
        kelly_factor = max(
            self.asset_cfg.kelly_floor_pct,
            min(kelly_factor, self.asset_cfg.kelly_max_pct),
        )

        # Calcola Sharpe prima dell'UPDATE
        sharpe = self._calculate_sharpe()

        self.db.execute(
            text("""
                UPDATE monthly_target_log SET
                  current_capital=:cap,
                  actual_return_pct=:ret,
                  run_rate_pct=:rr,
                  status=:status,
                  total_trades=:trades,
                  kelly_factor=:kf,
                  sizing_mode=:sm,
                  sharpe_ratio=:sharpe,
                  last_updated=:ts
                WHERE year_month=:ym AND is_paper=:ip
            """),
            {
                "cap": float(current),
                "ret": round(actual_return, 6),
                "rr": round(run_rate, 6),
                "status": status,
                "trades": trade_count,
                "kf": round(kelly_factor, 6),
                "sm": sizing_mode,
                "sharpe": sharpe,
                "ts": now,
                "ym": self.year_month,
                "ip": self.is_paper,
            },
        )
        self.db.commit()

        result = {
            "year_month": self.year_month,
            "actual_return_pct": round(actual_return * 100, 2),
            "run_rate_pct": round(run_rate * 100, 2),
            "target_pct": TARGET_MONTHLY_RETURN * 100,
            "target_progress": round(target_progress * 100, 1),
            "status": status,
            "kelly_raw": round(kelly_raw, 4),
            "kelly_factor": round(kelly_factor, 4),
            "sizing_mode": sizing_mode,
            "days_remaining": days_remaining,
            "sharpe_ratio": sharpe,
        }

        logger.info("monthly_target_updated", **result)
        return result

    @staticmethod
    def _calculate_kelly(
        win_rate: float,
        avg_win_loss_ratio: float,
    ) -> float:
        """
        f* = (w * b - (1-w)) / b
        dove b = avg_win / avg_loss (win_loss_ratio)
        """
        if avg_win_loss_ratio <= 0 or win_rate <= 0:
            return KELLY_FLOOR_PCT
        w = win_rate
        b = avg_win_loss_ratio
        kelly = (w * b - (1 - w)) / b
        return max(kelly, 0.0)  # Kelly non può essere negativo in produzione

    def get_position_size(
        self,
        current_capital: float,
        price: float,
        asset_class: Optional[AssetClass] = None,
    ) -> float:
        import math as _math
        cfg = get_asset_class_config(
            asset_class or self.asset_class
        )
        row = self.db.execute(
            text("""
                SELECT kelly_factor, status FROM monthly_target_log
                WHERE year_month=:ym AND is_paper=:ip
            """),
            {"ym": self.year_month, "ip": self.is_paper},
        ).fetchone()

        if not row or row[1] == "capital_preservation":
            logger.warning(
                "position_size_blocked",
                reason=row[1] if row else "no_record",
            )
            return 0.0

        kelly_factor = float(row[0] or cfg.kelly_floor_pct)
        position_value = current_capital * kelly_factor
        raw_qty = position_value / price if price > 0 else 0.0

        if cfg.fractional_qty:
            return round(raw_qty, 8)
        else:
            return float(_math.floor(raw_qty))  # intero per stock e PM

    def is_promote_eligible_monthly(self) -> dict:
        """
        Controlla se il target mensile è soddisfatto per la promozione.
        Richiede almeno 30 giorni di dati e run-rate >= 8%.
        """
        row = self.db.execute(
            text("""
                SELECT actual_return_pct, run_rate_pct, total_trades,
                       status, last_updated
                FROM monthly_target_log
                WHERE year_month=:ym AND is_paper=:ip
            """),
            {"ym": self.year_month, "ip": self.is_paper},
        ).fetchone()

        if not row:
            return {"eligible": False, "reason": "no_monthly_data"}

        actual_ret, run_rate, trades, status, last_updated = row
        days_of_data = (
            datetime.now(timezone.utc) - last_updated.replace(tzinfo=timezone.utc)
        ).days if last_updated else 0

        # Usa actual_return se >= 30 giorni, run_rate se < 30 giorni
        effective_return = float(actual_ret or 0)
        if days_of_data < 30:
            effective_return = float(run_rate or 0)

        eligible = (
            effective_return >= TARGET_MONTHLY_RETURN * 0.80  # almeno 8%
            and status not in ("capital_preservation",)
            and trades >= 30
        )

        return {
            "eligible": eligible,
            "effective_return_pct": round(effective_return * 100, 2),
            "target_pct": TARGET_MONTHLY_RETURN * 100,
            "days_of_data": days_of_data,
            "status": status,
            "trades": trades,
            "reason": (
                "monthly_target_met" if eligible
                else f"return {effective_return*100:.1f}% < {TARGET_MONTHLY_RETURN*0.8*100:.1f}% min"
            ),
        }
