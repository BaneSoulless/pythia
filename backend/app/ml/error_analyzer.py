"""
Error Analysis and Learning System
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.models import Trade, LearningExperience
import numpy as np


class ErrorAnalyzer:
    """
    Analyzes trading errors and provides learning feedback
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_trade(self, trade: Trade) -> Dict:
        """
        Analyze a single trade for errors or success patterns
        """
        analysis = {
            "trade_id": trade.id,
            "success": False,
            "error_type": None,
            "lessons": []
        }
        
        if trade.side == "sell" and trade.pnl is not None:
            if trade.pnl > 0:
                analysis["success"] = True
                analysis["lessons"].append(f"Profitable trade: +{trade.pnl:.2f}€")
            else:
                analysis["error_type"] = "loss"
                analysis["lessons"].append(f"Loss incurred: {trade.pnl:.2f}€")
                
                # Analyze why
                if trade.ai_confidence and trade.ai_confidence < 0.5:
                    analysis["lessons"].append("Low confidence trade - consider raising threshold")
        
        return analysis
    
    def get_recent_performance(
        self, 
        portfolio_id: int, 
        days: int = 7
    ) -> Dict:
        """
        Analyze recent trading performance
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        recent_trades = self.db.query(Trade).filter(
            Trade.portfolio_id == portfolio_id,
            Trade.executed_at >= cutoff_date,
            Trade.side == "sell"  # Only completed trades
        ).all()
        
        if not recent_trades:
            return {"total_trades": 0}
        
        total_pnl = sum(t.pnl for t in recent_trades if t.pnl)
        winning_trades = len([t for t in recent_trades if t.pnl and t.pnl > 0])
        losing_trades = len([t for t in recent_trades if t.pnl and t.pnl < 0])
        
        return {
            "total_trades": len(recent_trades),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": winning_trades / len(recent_trades) if recent_trades else 0,
            "total_pnl": total_pnl,
            "avg_pnl": total_pnl / len(recent_trades)
        }
    
    def identify_patterns(self, portfolio_id: int) -> List[Dict]:
        """
        Identify patterns in trading behavior
        """
        trades = self.db.query(Trade).filter(
            Trade.portfolio_id == portfolio_id,
            Trade.side == "sell"
        ).order_by(Trade.executed_at.desc()).limit(50).all()
        
        patterns = []
        
        # Pattern 1: Time of day analysis
        time_performance = {}
        for trade in trades:
            hour = trade.executed_at.hour
            if hour not in time_performance:
                time_performance[hour] = []
            if trade.pnl:
                time_performance[hour].append(trade.pnl)
        
        # Find best/worst hours
        hour_avgs = {h: np.mean(pnls) for h, pnls in time_performance.items()}
        if hour_avgs:
            best_hour = max(hour_avgs, key=hour_avgs.get)
            worst_hour = min(hour_avgs, key=hour_avgs.get)
            
            patterns.append({
                "type": "time_of_day",
                "insight": f"Best trading hour: {best_hour}:00, Worst: {worst_hour}:00"
            })
        
        # Pattern 2: Confidence correlation
        if any(t.ai_confidence for t in trades):
            high_conf_trades = [t for t in trades if t.ai_confidence and t.ai_confidence > 0.7]
            low_conf_trades = [t for t in trades if t.ai_confidence and t.ai_confidence < 0.5]
            
            if high_conf_trades and low_conf_trades:
                high_conf_pnl = np.mean([t.pnl for t in high_conf_trades if t.pnl])
                low_conf_pnl = np.mean([t.pnl for t in low_conf_trades if t.pnl])
                
                patterns.append({
                    "type": "confidence_correlation",
                    "insight": f"High confidence avg P&L: {high_conf_pnl:.2f}€, Low: {low_conf_pnl:.2f}€"
                })
        
        return patterns
    
    def generate_learning_experience(
        self,
        state: Dict,
        action: Dict,
        reward: float,
        next_state: Dict,
        done: bool
    ) -> LearningExperience:
        """
        Create a learning experience for the RL agent
        """
        experience = LearningExperience(
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done
        )
        
        self.db.add(experience)
        self.db.commit()
        
        return experience
    
    def get_strategy_recommendations(self, portfolio_id: int) -> List[str]:
        """
        Generate strategy recommendations based on analysis
        """
        recommendations = []
        
        # Analyze recent performance
        perf = self.get_recent_performance(portfolio_id, days=30)
        
        if perf.get("total_trades", 0) < 10:
            recommendations.append("Gather more trading data before adjusting strategy")
            return recommendations
        
        # Win rate analysis
        win_rate = perf.get("win_rate", 0)
        if win_rate < 0.4:
            recommendations.append("Win rate low (<40%) - Consider more conservative entry criteria")
        elif win_rate > 0.6:
            recommendations.append("Win rate good (>60%) - Current strategy is working well")
        
        # P&L analysis
        avg_pnl = perf.get("avg_pnl", 0)
        if avg_pnl < 0:
            recommendations.append("Negative average P&L - Reduce position sizes or tighten stop-losses")
        
        # Pattern-based recommendations
        patterns = self.identify_patterns(portfolio_id)
        for pattern in patterns:
            if pattern["type"] == "confidence_correlation":
                recommendations.append("Consider filtering trades with AI confidence > 0.6")
        
        return recommendations
