from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pythia.infrastructure.persistence.database import get_db
from pythia.infrastructure.persistence.models import Portfolio, Position, User
from pythia.core.auth import get_current_user
from pythia.core.errors import ResourceNotFoundError, TradingBotError, ErrorCode

router = APIRouter()

@router.get("/", response_model=dict)
def get_portfolio(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    "Get current user's portfolio status"
    portfolio = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).first()
    if not portfolio:
        # Create initial portfolio if not exists
        portfolio = Portfolio(user_id=current_user.id, balance=10000.0)
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)
    
    return {
        "id": portfolio.id,
        "balance": portfolio.balance,
        "total_value": portfolio.total_value,
        "cash": portfolio.balance,  # Simplified for now
        "positions_count": len(portfolio.positions)
    }

@router.get("/positions", response_model=List[dict])
def get_portfolio_positions(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    "Get open positions with pagination"
    portfolio = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).first()
    if not portfolio:
        raise ResourceNotFoundError("Portfolio")
        
    positions = db.query(Position).filter(
        Position.portfolio_id == portfolio.id,
        Position.status == "OPEN"
    ).offset(skip).limit(limit).all()
    
    return [
        {
            "symbol": p.symbol,
            "quantity": p.quantity,
            "entry_price": p.entry_price,
            "current_price": p.current_price,
            "pnl": p.pnl,
            "pnl_percent": p.pnl_percent
        }
        for p in positions
    ]

@router.get("/history", response_model=dict)
def get_portfolio_history(
    period: str = "1M",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    "Get portfolio value history"
    # Placeholder for now
    return {
        "dates": [],
        "values": []
    }
