from fastapi import Depends
from pythia.core.config import settings
from pythia.core.ports.repository import IPortfolioRepository, ITradeRepository
from pythia.infrastructure.persistence.database import get_db
from pythia.infrastructure.persistence.repositories import (
    SqlAlchemyPortfolioRepository,
    SqlAlchemyTradeRepository,
)
from pythia.infrastructure.pm_adapters.polymarket import MockPolymarketAdapter
from sqlalchemy.orm import Session


def get_portfolio_repository(db: Session = Depends(get_db)) -> IPortfolioRepository:
    return SqlAlchemyPortfolioRepository(db)

def get_trade_repository(db: Session = Depends(get_db)) -> ITradeRepository:
    return SqlAlchemyTradeRepository(db)

def get_pm_adapter() -> MockPolymarketAdapter:
    # Use dummy keys from settings if available, else fallback
    api_key = getattr(settings, "PM_PAPER_API_KEY", "mock-key")
    api_secret = getattr(settings, "PM_PAPER_SECRET", "mock-secret")
    return MockPolymarketAdapter(api_key=api_key, api_secret=api_secret)

# Add EnhancedTradingEngine provision when ready
