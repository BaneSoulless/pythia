"""
Performance Prediction Module

Predicts future portfolio performance based on:
- Historical returns
- AI model confidence
- Market conditions
- Risk metrics
"""
import logging
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.models import Trade, Portfolio

logger = logging.getLogger(__name__)


class PerformancePredictor:
    """
    Predicts portfolio performance using statistical methods
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def predict_next_day_return(self, portfolio_id: int) -> Dict:
        """
        Predict next day's expected return
        
        Returns:
            Dict with prediction, confidence, and range
        """
        try:
            # Get recent trades
            recent_trades = self.db.query(Trade).filter(
                Trade.portfolio_id == portfolio_id,
                Trade.side == "sell",
                Trade.executed_at >= datetime.utcnow() - timedelta(days=30)
            ).all()
            
            if len(recent_trades) < 5:
                return {
                    "prediction": 0.0,
                    "confidence": 0.0,
                    "range": {"low": 0.0, "high": 0.0},
                    "message": "Insufficient data for prediction"
                }
            
            # Calculate returns
            returns = [t.pnl for t in recent_trades if t.pnl is not None]
            
            # Statistical measures
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            # Weighted by AI confidence
            weighted_returns = []
            for trade in recent_trades:
                if trade.pnl is not None and trade.ai_confidence is not None:
                    weighted_returns.append(trade.pnl * trade.ai_confidence)
            
            if weighted_returns:
                weighted_mean = np.mean(weighted_returns)
            else:
                weighted_mean = mean_return
            
            # Confidence based on consistency
            win_rate = len([r for r in returns if r > 0]) / len(returns)
            consistency = 1 - (std_return / (abs(mean_return) + 1))
            confidence = min(win_rate * consistency, 1.0)
            
            # Prediction range (1 std dev)
            prediction_range = {
                "low": weighted_mean - std_return,
                "high": weighted_mean + std_return
            }
            
            logger.info(f"Performance prediction: {weighted_mean:.2f} (confidence: {confidence:.2f})")
            
            return {
                "prediction": float(weighted_mean),
                "confidence": float(confidence),
                "range": prediction_range,
                "historical_mean": float(mean_return),
                "volatility": float(std_return),
                "win_rate": float(win_rate),
                "trades_analyzed": len(returns)
            }
            
        except Exception as e:
            logger.error(f"Error predicting performance: {e}")
            return {
                "prediction": 0.0,
                "confidence": 0.0,
                "range": {"low": 0.0, "high": 0.0},
                "error": str(e)
            }
    
    def predict_monthly_performance(self, portfolio_id: int) -> Dict:
        """
        Predict monthly performance trajectory
        """
        try:
            daily = self.predict_next_day_return(portfolio_id)
            
            if daily["confidence"] < 0.3:
                return {
                    "predictions": [],
                    "message": "Low confidence - need more trading data"
                }
            
            # Monte Carlo simulation
            predictions = []
            current_value = self.db.query(Portfolio).filter(
                Portfolio.id == portfolio_id
            ).first().total_value
            
            for day in range(30):
                # Sample from distribution
                expected_return = daily["prediction"]
                volatility = daily["volatility"]
                
                # Random walk with drift
                daily_return = np.random.normal(expected_return, volatility)
                current_value += daily_return
                
                predictions.append({
                    "day": day + 1,
                    "value": float(current_value),
                    "return": float(daily_return)
                })
            
            return {
                "predictions": predictions,
                "initial_value": float(self.db.query(Portfolio).filter(
                    Portfolio.id == portfolio_id
                ).first().total_value),
                "expected_final_value": float(current_value),
                "confidence": daily["confidence"]
            }
            
        except Exception as e:
            logger.error(f"Error predicting monthly performance: {e}")
            return {"predictions": [], "error": str(e)}
    
    def get_risk_metrics(self, portfolio_id: int) -> Dict:
        """
        Calculate risk metrics
        """
        try:
            recent_trades = self.db.query(Trade).filter(
                Trade.portfolio_id == portfolio_id,
                Trade.side == "sell",
                Trade.executed_at >= datetime.utcnow() - timedelta(days=30)
            ).all()
            
            if not recent_trades:
                return {}
            
            returns = [t.pnl for t in recent_trades if t.pnl is not None]
            
            if not returns:
                return {}
            
            # Sharpe ratio (simplified, assuming risk-free rate = 0)
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe = mean_return / std_return if std_return > 0 else 0
            
            # Maximum drawdown
            cumulative = np.cumsum(returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = cumulative - running_max
            max_drawdown = np.min(drawdown)
            
            # Value at Risk (95% confidence)
            var_95 = np.percentile(returns, 5)
            
            return {
                "sharpe_ratio": float(sharpe),
                "max_drawdown": float(max_drawdown),
                "value_at_risk_95": float(var_95),
                "volatility": float(std_return),
                "mean_return": float(mean_return)
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return {"error": str(e)}


# Global instance
performance_predictor = None

def get_performance_predictor(db: Session) -> PerformancePredictor:
    """Get or create performance predictor instance"""
    return PerformancePredictor(db)
