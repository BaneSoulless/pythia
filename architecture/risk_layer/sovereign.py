"""
Risk Layer - Sovereign Kernel
Immutable Safety Logic, VaR, Kelly Criterion
"""
import numpy as np
from scipy.stats import norm
import logging
from typing import List, Dict, Any

logger = logging.getLogger("SovereignKernel")

class RiskManager:
    """
    Sovereign Risk Kernel.
    Sits above AI to prevent catastrophic actions.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_drawdown_limit = 0.015 # 1.5% per hour
        self.circuit_tripped = False
    
    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """Calculate Historical Value at Risk."""
        if not returns: return 0.0
        return np.percentile(returns, 100 * (1 - confidence))

    def kelly_criterion(self, win_rate: float, win_loss_ratio: float) -> float:
        """
        Calculate Kelly Fraction.
        f* = p - q/b
        """
        if win_loss_ratio <= 0: return 0.0
        f = win_rate - (1 - win_rate) / win_loss_ratio
        return max(0.0, f)

    def validate_trade(self, signal: Dict[str, Any], portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and size trade.
        Returns modified signal or None if rejected.
        """
        if self.circuit_tripped:
            logger.warning("Trade Rejected: CIRCUIT BREAKER ACTIVE")
            return None

        # Check Circuit Breaker (Simulation)
        # expected portfolio_state to have 'hourly_drawdown'
        if portfolio_state.get('hourly_drawdown', 0) > self.max_drawdown_limit:
            self.circuit_tripped = True
            logger.critical("CIRCUIT BREAKER TRIPPED! HALTING TRADING.")
            return None

        # Kelly Sizing
        # Mock performace stats from portfolio or use defaults
        win_rate = portfolio_state.get('win_rate', 0.55)
        wl_ratio = portfolio_state.get('wl_ratio', 1.5)
        
        kelly_fraction = self.kelly_criterion(win_rate, wl_ratio)
        # Conservative Half-Kelly
        safe_fraction = kelly_fraction * 0.5
        
        # Scale by AI Confidence
        confidence = signal.get('confidence', 0.0)
        final_size_ratio = safe_fraction * confidence
        
        signal['size_ratio'] = final_size_ratio
        signal['risk_check'] = 'PASS'
        
        # Filter tiny trades
        if final_size_ratio < 0.01:
            logger.info("Trade Rejected: Kelly size too small")
            return None
            
        return signal

    def reset_breaker(self):
        logger.warning("Manual Reset of Circuit Breaker")
        self.circuit_tripped = False
