"""
Specialized Trading Agents

Domain-specific agents for different aspects of trading
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
import numpy as np
logger = logging.getLogger(__name__)

class TechnicalAnalysisAgent:
    """
    Agent specialized in technical analysis and pattern recognition
    """

    def __init__(self):
        self.name = 'Technical Analyst'

    def analyze_trend(self, prices: List[float]) -> Dict:
        """
        Analyze price trend
        
        Returns:
            Direction (bullish/bearish/neutral), strength (0-1)
        """
        if len(prices) < 10:
            return {'direction': 'neutral', 'strength': 0.0, 'confidence': 0.0}
        sma_short = np.mean(prices[-5:])
        sma_long = np.mean(prices[-20:]) if len(prices) >= 20 else np.mean(prices)
        if sma_short > sma_long * 1.02:
            direction = 'bullish'
            strength = min((sma_short - sma_long) / sma_long * 10, 1.0)
        elif sma_short < sma_long * 0.98:
            direction = 'bearish'
            strength = min((sma_long - sma_short) / sma_long * 10, 1.0)
        else:
            direction = 'neutral'
            strength = 0.5
        return {'direction': direction, 'strength': strength, 'confidence': min(len(prices) / 50, 1.0), 'sma_short': sma_short, 'sma_long': sma_long}

    def detect_support_resistance(self, prices: List[float], window: int=20) -> Dict:
        """Identify support and resistance levels"""
        if len(prices) < window:
            return {'support': None, 'resistance': None}
        recent_prices = prices[-window:]
        support = min(recent_prices)
        resistance = max(recent_prices)
        return {'support': support, 'resistance': resistance, 'current_position': (prices[-1] - support) / (resistance - support) if resistance > support else 0.5}

    def check_bollinger_bands(self, prices: List[float], period: int=20, std_dev: int=2) -> Dict:
        """
        Check Bollinger Bands position
        
        Returns position relative to bands and signals
        """
        if len(prices) < period:
            return {'signal': 'neutral', 'position': 'middle'}
        recent = prices[-period:]
        sma = np.mean(recent)
        std = np.std(recent)
        upper_band = sma + std_dev * std
        lower_band = sma - std_dev * std
        current = prices[-1]
        if current > upper_band:
            signal = 'overbought'
            position = 'above_upper'
        elif current < lower_band:
            signal = 'oversold'
            position = 'below_lower'
        else:
            signal = 'neutral'
            if current > sma:
                position = 'upper_half'
            else:
                position = 'lower_half'
        return {'signal': signal, 'position': position, 'upper_band': upper_band, 'middle_band': sma, 'lower_band': lower_band, 'current_price': current}

class SentimentAnalysisAgent:
    """
    Agent specialized in market sentiment analysis
    """

    def __init__(self):
        self.name = 'Sentiment Analyst'

    def analyze_volume(self, volumes: List[float]) -> Dict:
        """
        Analyze trading volume patterns
        """
        if len(volumes) < 10:
            return {'sentiment': 'neutral', 'strength': 0.0}
        avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
        recent_volume = volumes[-1]
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
        if volume_ratio > 1.5:
            sentiment = 'strong_interest'
            strength = min(volume_ratio / 3, 1.0)
        elif volume_ratio > 1.2:
            sentiment = 'increasing_interest'
            strength = 0.6
        elif volume_ratio < 0.7:
            sentiment = 'declining_interest'
            strength = 0.3
        else:
            sentiment = 'normal'
            strength = 0.5
        return {'sentiment': sentiment, 'strength': strength, 'volume_ratio': volume_ratio, 'avg_volume': avg_volume, 'recent_volume': recent_volume}

    def assess_market_conditions(self, market_data: Dict) -> Dict:
        """Overall market condition assessment"""
        return {'overall_sentiment': 'neutral', 'market_condition': 'normal', 'recommendation': 'monitor', 'confidence': 0.5}

class RiskManagementAgent:
    """
    Agent specialized in risk assessment and management
    """

    def __init__(self, max_position_size: float=0.1, max_portfolio_risk: float=0.15):
        self.name = 'Risk Manager'
        self.max_position_size = max_position_size
        self.max_portfolio_risk = max_portfolio_risk

    def assess_trade_risk(self, portfolio_value: float, position_size: float, symbol_volatility: float) -> Dict:
        """
        Assess risk of a proposed trade
        
        Returns approval and risk metrics
        """
        position_pct = position_size / portfolio_value if portfolio_value > 0 else 0
        if position_pct > self.max_position_size:
            return {'approved': False, 'reason': f'Position size {position_pct:.1%} exceeds limit {self.max_position_size:.1%}', 'risk_score': 1.0}
        risk_score = position_pct / self.max_position_size * symbol_volatility
        approved = risk_score < 0.7
        return {'approved': approved, 'risk_score': risk_score, 'position_pct': position_pct, 'reason': 'Acceptable risk' if approved else f'Risk score {risk_score:.2f} too high'}

    def calculate_position_size(self, portfolio_value: float, confidence: float, volatility: float) -> float:
        """
        Calculate optimal position size using Kelly Criterion (simplified)
        """
        base_size = self.max_position_size * portfolio_value
        confidence_factor = confidence
        volatility_factor = 1 / (1 + volatility)
        optimal_size = base_size * confidence_factor * volatility_factor
        return min(optimal_size, base_size)

class ExecutionAgent:
    """
    Agent specialized in trade execution optimization
    """

    def __init__(self):
        self.name = 'Execution Specialist'

    def determine_entry_timing(self, current_price: float, support: float, resistance: float, trend: str) -> Dict:
        """
        Determine optimal entry timing
        """
        price_range = resistance - support if resistance > support else current_price * 0.1
        position_in_range = (current_price - support) / price_range if price_range > 0 else 0.5
        if trend == 'bullish':
            if position_in_range < 0.3:
                timing = 'excellent'
                urgency = 0.9
            elif position_in_range < 0.6:
                timing = 'good'
                urgency = 0.6
            else:
                timing = 'wait'
                urgency = 0.2
        elif trend == 'bearish':
            timing = 'avoid'
            urgency = 0.0
        else:
            timing = 'neutral'
            urgency = 0.5
        return {'timing': timing, 'urgency': urgency, 'recommended_price': support + price_range * 0.3, 'stop_loss': support * 0.98}

class AgentCoordinator:
    """
    Coordinates multiple specialized agents for trading decisions
    """

    def __init__(self):
        self.technical_agent = TechnicalAnalysisAgent()
        self.sentiment_agent = SentimentAnalysisAgent()
        self.risk_agent = RiskManagementAgent()
        self.execution_agent = ExecutionAgent()

    def evaluate_trade_opportunity(self, symbol: str, prices: List[float], volumes: List[float], portfolio_value: float) -> Dict:
        """
        Coordinate all agents to evaluate a trade opportunity
        """
        trend_analysis = self.technical_agent.analyze_trend(prices)
        support_resistance = self.technical_agent.detect_support_resistance(prices)
        bollinger = self.technical_agent.check_bollinger_bands(prices)
        volume_analysis = self.sentiment_agent.analyze_volume(volumes)
        volatility = np.std(prices[-20:]) / np.mean(prices[-20:]) if len(prices) >= 20 else 0.1
        position_size = self.risk_agent.calculate_position_size(portfolio_value, trend_analysis['confidence'], volatility)
        risk_assessment = self.risk_agent.assess_trade_risk(portfolio_value, position_size, volatility)
        execution_timing = self.execution_agent.determine_entry_timing(prices[-1], support_resistance.get('support', prices[-1] * 0.95), support_resistance.get('resistance', prices[-1] * 1.05), trend_analysis['direction'])
        overall_score = trend_analysis['strength'] * 0.3 + volume_analysis['strength'] * 0.2 + (1 - risk_assessment['risk_score']) * 0.3 + execution_timing['urgency'] * 0.2
        if not risk_assessment['approved']:
            recommendation = 'reject'
        elif overall_score > 0.7:
            recommendation = 'strong_buy'
        elif overall_score > 0.5:
            recommendation = 'buy'
        else:
            recommendation = 'hold'
        return {'symbol': symbol, 'recommendation': recommendation, 'overall_score': overall_score, 'position_size': position_size, 'technical_analysis': trend_analysis, 'sentiment_analysis': volume_analysis, 'risk_assessment': risk_assessment, 'execution_timing': execution_timing, 'bollinger_bands': bollinger, 'support_resistance': support_resistance}
agent_coordinator = AgentCoordinator()