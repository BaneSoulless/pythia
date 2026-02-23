from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pythia.infrastructure.persistence.database import get_db
from pythia.infrastructure.persistence.models import User, Portfolio, Trade
from pythia.core.auth import get_current_user
from pythia.core.errors import TradingBotError, ResourceNotFoundError
import structlog
from typing import List
logger = structlog.get_logger()
router = APIRouter()

@router.get('/', response_model=list)
async def get_trades(skip: int=Query(0, ge=0), limit: int=Query(50, ge=1, le=100), current_user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    """Get trade history with pagination"""
    try:
        portfolio = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).first()
        if not portfolio:
            raise ResourceNotFoundError('Portfolio not found')
        trades = db.query(Trade).filter(Trade.portfolio_id == portfolio.id).order_by(Trade.executed_at.desc()).offset(skip).limit(limit).all()
        return [{'id': t.id, 'symbol': t.symbol, 'side': t.side, 'quantity': t.quantity, 'price': t.price, 'total': t.quantity * t.price, 'executed_at': t.executed_at, 'pnl': t.pnl} for t in trades]
    except ResourceNotFoundError as e:
        logger.warning('resource_not_found', error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error('get_trades_error', error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail=f'Failed to fetch trades: {str(e)}')

@router.get('/statistics')
async def get_trade_statistics(db: Session=Depends(get_db)):
    """Get trading statistics"""
    portfolio = db.query(Portfolio).first()
    if not portfolio:
        return {}
    all_trades = db.query(Trade).filter(Trade.portfolio_id == portfolio.id, Trade.side == 'sell').all()
    if not all_trades:
        return {'total_trades': 0, 'total_pnl': 0, 'win_rate': 0}
    winning_trades = [t for t in all_trades if t.pnl and t.pnl > 0]
    total_pnl = sum((t.pnl for t in all_trades if t.pnl))
    return {'total_trades': len(all_trades), 'winning_trades': len(winning_trades), 'losing_trades': len(all_trades) - len(winning_trades), 'win_rate': len(winning_trades) / len(all_trades), 'total_pnl': total_pnl, 'avg_pnl': total_pnl / len(all_trades)}