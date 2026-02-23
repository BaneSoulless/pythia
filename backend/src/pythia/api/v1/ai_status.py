"""
AI Status API Endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pythia.infrastructure.persistence.database import get_db
from pythia.infrastructure.persistence.models import Portfolio
from pythia.application.ai.error_analyzer import ErrorAnalyzer
router = APIRouter()

@router.get('/status')
async def get_ai_status(db: Session=Depends(get_db)):
    """Get current AI learning status"""
    portfolio = db.query(Portfolio).first()
    if not portfolio:
        return {'is_learning': False, 'epsilon': 1.0, 'total_experiences': 0}
    return {'is_learning': True, 'phase': 'exploration', 'epsilon': 0.5, 'total_experiences': 0, 'current_strategy': 'Conservative DQN'}

@router.get('/performance')
async def get_ai_performance(db: Session=Depends(get_db)):
    """Get AI performance metrics"""
    portfolio = db.query(Portfolio).first()
    if not portfolio:
        return {}
    analyzer = ErrorAnalyzer(db)
    performance = analyzer.get_recent_performance(portfolio.id, days=30)
    return performance

@router.get('/recommendations')
async def get_recommendations(db: Session=Depends(get_db)):
    """Get strategy recommendations from error analysis"""
    portfolio = db.query(Portfolio).first()
    if not portfolio:
        return {'recommendations': []}
    analyzer = ErrorAnalyzer(db)
    recommendations = analyzer.get_strategy_recommendations(portfolio.id)
    return {'recommendations': recommendations}