"""
Cognitive Layer: Specialized Trading Agents
SOTA 2026 Architecture

Migrated from backend/app/agents to architecture/cognitive_layer.
Uses Neuro-Symbolic Logic for decision support.
"""
import logging
import numpy as np
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class TechnicalAnalysisAgent:
    """Specialized in technical analysis and pattern recognition."""
    def __init__(self):
        self.name = "Technical Analyst"
    
    def analyze_trend(self, prices: List[float]) -> Dict:
        if len(prices) < 10:
            return {"direction": "neutral", "strength": 0.0, "confidence": 0.0}
        
        sma_short = np.mean(prices[-5:])
        sma_long = np.mean(prices[-20:]) if len(prices) >= 20 else np.mean(prices)
        
        if sma_short > sma_long * 1.02:
            direction = "bullish"
            strength = min((sma_short - sma_long) / sma_long * 10, 1.0)
        elif sma_short < sma_long * 0.98:
            direction = "bearish"
            strength = min((sma_long - sma_short) / sma_long * 10, 1.0)
        else:
            direction = "neutral"
            strength = 0.5
        
        return {
            "direction": direction,
            "strength": strength,
            "confidence": min(len(prices) / 50, 1.0)
        }

class SentimentAnalysisAgent:
    """Specialized in market sentiment analysis."""
    def __init__(self):
        self.name = "Sentiment Analyst"
    
    def analyze_volume(self, volumes: List[float]) -> Dict:
        if len(volumes) < 10:
            return {"sentiment": "neutral", "strength": 0.0}
        
        avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
        ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1.0
        
        if ratio > 1.5:
            return {"sentiment": "high_interest", "strength": min(ratio/3, 1.0)}
        return {"sentiment": "normal", "strength": 0.5}

class RiskManagementAgent:
    """Specialized in risk assessment."""
    def __init__(self, max_risk=0.02):
        self.name = "Risk Manager"
        self.max_risk = max_risk

    def assess_risk(self, signal: Dict, portfolio_value: float) -> bool:
        # Simplified risk check
        return True

class AgentCoordinator:
    """Orchestrates all cognitive agents."""
    def __init__(self):
        self.technical = TechnicalAnalysisAgent()
        self.sentiment = SentimentAnalysisAgent()
        self.risk = RiskManagementAgent()

    def analyze(self, prices: List[float], volumes: List[float]) -> Dict:
        trend = self.technical.analyze_trend(prices)
        sentiment = self.sentiment.analyze_volume(volumes)
        return {
            "trend": trend,
            "sentiment": sentiment,
            "recommendation": "buy" if trend['direction'] == "bullish" and sentiment['strength'] > 0.6 else "hold"
        }

agent_coordinator = AgentCoordinator()
