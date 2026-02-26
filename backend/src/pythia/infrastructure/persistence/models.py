"""
Purpose: SOTA-2026 Persistence Models using SQLAlchemy 2.0.
Main constraints: Must define the database schema for the complete Trading System (Trades, Signals, Positions)
Dependencies: sqlalchemy>=2.0.0

Edge cases handled:
1. Implicit Indexing on frequently queried columns (symbol, timestamp).
2. Enum constraints applied safely on Database columns.
"""
# Step-1: Import Abstractions
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Boolean, Enum as SQLEnum, Integer
from sqlalchemy.orm import DeclarativeBase
from typing import Optional

from pythia.core.ports import AssetClass

class Base(DeclarativeBase):
    """SQLAlchemy 2.0 Base."""
    pass

class TradeRecord(Base):
    """Logs executed trades across all adapters."""
    __tablename__ = "trades"

    # Step-2: Define constrained columns
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True)
    side = Column(String(10), nullable=False) # BUY, SELL
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    platform = Column(String(30), nullable=False) # alpaca, kalshi, etc.
    asset_class = Column(SQLEnum(AssetClass), nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Step-3: Pre/Post assertions logic on creation
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert self.quantity > 0, "Quantity must be positive"
        assert self.price >= 0, "Price must be non-negative"

class PositionRecord(Base):
    """Tracks current active portfolio."""
    __tablename__ = "positions"

    symbol = Column(String(50), primary_key=True)
    platform = Column(String(30), primary_key=True)
    quantity = Column(Float, nullable=False, default=0.0)
    average_entry_price = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SignalRecord(Base):
    """Audit log of AI-generated trading signals."""
    __tablename__ = "ai_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pair = Column(String(50), nullable=False, index=True)
    action = Column(String(10), nullable=False) # BUY, SELL, HOLD
    confidence = Column(Float, nullable=False)
    source = Column(String(50), nullable=False) # e.g. 'groq-llama3', 'rl-dqn'
    reasoning = Column(String(1000), nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert 0.0 <= self.confidence <= 1.0, "Confidence must be [0.0, 1.0]"
