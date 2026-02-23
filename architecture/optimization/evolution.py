"""
Optimization Layer - Dynamic Hyper-Parameter Evolution
Auto-Tuning strategies based on Market Regime.
"""
import optuna
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List

logger = logging.getLogger("EvolutionDaemon")
optuna.logging.set_verbosity(optuna.logging.WARNING)

class EvolutionDaemon:
    def __init__(self):
        self.active_regime = "unknown"
        self.best_params = {}

    def detect_regime(self, candles: List[Dict[str, Any]]) -> str:
        """
        Detect Market Regime: TRENDING, RANGING, VOLATILE.
        Uses ATR and ADX proxy logic.
        """
        if len(candles) < 20: return "unknown"
        
        df = pd.DataFrame(candles)
        df['tr'] = df[['high', 'low', 'close']].apply(lambda x: max(x['high']-x['low'], abs(x['high']-x['close'].shift()), abs(x['low']-x['close'].shift())), axis=1)
        atr = df['tr'].rolling(14).mean().iloc[-1]
        std = df['close'].rolling(20).std().iloc[-1]
        
        # Simple heuristics
        price = df['close'].iloc[-1]
        volatility_ratio = atr / price
        
        if volatility_ratio > 0.02: # > 2% daily range approx
            return "VOLATILE"
            
        ema_fast = df['close'].ewm(span=12).mean().iloc[-1]
        ema_slow = df['close'].ewm(span=26).mean().iloc[-1]
        
        if abs(ema_fast - ema_slow) / price > 0.005:
            return "TRENDING"
            
        return "RANGING"

    def objective(self, trial: optuna.Trial, regime: str) -> float:
        """
        Optimization Objective.
        In detailed implementation, this runs a localized backtest.
        Here we optimize for a theoretical 'fitness' score based on heuristics.
        """
        rsi_len = trial.suggest_int('rsi_length', 5, 30)
        macd_fast = trial.suggest_int('macd_fast', 8, 20)
        
        # Heuristic Fitness Function (Mocking Backtest Result)
        score = 0.0
        
        if regime == "VOLATILE":
            # Prefer faster reactions but avoiding noise? 
            # Actually, volatile -> larger lookback to filter noise?
            # Let's say we prefer higher RSI length in volatility to avoid false signals
            score = -abs(rsi_len - 21) # Target 21
            
        elif regime == "TRENDING":
            # Trend following -> standard MACD
            score = -abs(macd_fast - 12)
            
        else: # RANGING
            # Oscillators work well, shorter RSI
            score = -abs(rsi_len - 7)
            
        return score

    def evolve(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run Optimization Cycle."""
        if not candles: return {}
        
        regime = self.detect_regime(candles)
        if regime != self.active_regime:
            logger.info(f"Market Regime Change Detected: {self.active_regime} -> {regime}")
            self.active_regime = regime
            
            # Re-Optimize
            study = optuna.create_study(direction='maximize')
            study.optimize(lambda t: self.objective(t, regime), n_trials=20)
            
            self.best_params = study.best_params
            logger.info(f"Evolution Complete. New Params: {self.best_params}")
            
        return self.best_params
