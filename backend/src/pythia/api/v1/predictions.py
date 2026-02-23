"""
Performance Prediction API Endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pythia.infrastructure.persistence.database import get_db
from pythia.application.ai.performance_prediction import get_performance_predictor
from pythia.core.errors import TradingBotError
router = APIRouter()
logger = logging.getLogger(__name__)

@router.get('/predict/next-day/{portfolio_id}')
async def predict_next_day(portfolio_id: int, db: Session=Depends(get_db)):
    """Predict next day's expected return"""
    predictor = get_performance_predictor(db)
    prediction = predictor.predict_next_day_return(portfolio_id)
    return prediction

@router.get('/predict/monthly/{portfolio_id}')
async def predict_monthly(portfolio_id: int, db: Session=Depends(get_db)):
    """Predict 30-day performance trajectory"""
    predictor = get_performance_predictor(db)
    prediction = predictor.predict_monthly_performance(portfolio_id)
    return prediction

@router.get('/risk-metrics/{portfolio_id}')
async def get_risk_metrics(portfolio_id: int, db: Session=Depends(get_db)):
    """Get portfolio risk metrics"""
    predictor = get_performance_predictor(db)
    metrics = predictor.get_risk_metrics(portfolio_id)
    return metrics