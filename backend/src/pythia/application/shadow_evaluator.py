"""ShadowEvaluator: parallel shadow agent for evolved config validation.

Executes the same decisions as the live engine using the evolved config
(pythia_params_evolved.yaml) but does NOT place real trades.
Records outcomes via ASIEvolveEngine.record_shadow_trade().
"""
from __future__ import annotations

import logging
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pythia.application.asi_evolve import ASIEvolveEngine

logger = logging.getLogger("PYTHIA-SHADOW")


class ShadowEvaluator:
    """Parallel shadow agent: receives signals, decides with evolved config,
    compares against real outcome, propagates to ASIEvolveEngine."""

    def __init__(self, asi_engine: "ASIEvolveEngine") -> None:
        self.asi_engine = asi_engine
        self.active = False
        self._evolved_config: Optional[dict] = None
        self._reload_config()

    def _reload_config(self) -> None:
        """Load pythia_params_evolved.yaml if available."""
        config = self.asi_engine.load_evolved_config()
        if config:
            self._evolved_config = config
            self.active = True
            logger.info(
                "[SHADOW] Config loaded — min_confidence=%s",
                config.get("ensemble", {}).get("min_confidence"),
            )
        else:
            self._evolved_config = None
            self.active = False
            logger.info("[SHADOW] Inactive — no evolved config available")

    def evaluate(
        self,
        signal_score: float,
        rl_score: float,
        specialized_score: float,
    ) -> Optional[float]:
        """Compute the shadow decision using the evolved config.

        Returns the combined confidence score, or None if inactive
        or below min_confidence threshold.
        """
        if not self.active or self._evolved_config is None:
            return None

        ensemble = self._evolved_config.get("ensemble", {})
        w_rl = ensemble.get("weight_rl", 0.35)
        w_sig = ensemble.get("weight_signal", 0.32)
        w_spe = ensemble.get("weight_specialized", 0.33)
        min_conf = ensemble.get("min_confidence", 0.65)

        combined = (
            w_rl * rl_score
            + w_sig * signal_score
            + w_spe * specialized_score
        )
        return combined if combined >= min_conf else None

    async def record_outcome(
        self,
        shadow_decision: Optional[float],
        actual_pnl: float,
        actual_win: bool,
    ) -> None:
        """Record a shadow trade outcome.

        If the promote threshold is reached, triggers automatic promotion.
        """
        if not self.active or shadow_decision is None:
            return

        promote_ready = self.asi_engine.record_shadow_trade(
            shadow_win=actual_win,
            shadow_pnl=actual_pnl,
        )

        if promote_ready:
            logger.info("[SHADOW] Promote threshold reached — attempting promotion")
            promoted = self.asi_engine.promote_evolved_config()
            if promoted:
                logger.info("[SHADOW] Evolved config promoted to production")
                self._reload_config()  # reset after promote
            else:
                logger.warning("[SHADOW] Promote blocked — metrics check failed")
