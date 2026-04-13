"""
Purpose: SOTA-2026 Persistence Models using SQLAlchemy 2.0.
Main constraints: Must define the database schema for the
complete Trading System (Trades, Signals, Positions).
Dependencies: sqlalchemy>=2.0.0

Edge cases handled:
1. Implicit Indexing on frequently queried columns (symbol, timestamp).
2. Enum constraints applied safely on Database columns.
"""

from datetime import UTC, datetime

from pythia.core.ports import AssetClass
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, relationship


def _utcnow():
    """Timezone-aware UTC timestamp factory."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 Base."""

    pass


class User(Base):
    """Application user with authentication credentials."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    portfolios = relationship("Portfolio", back_populates="user")


class Portfolio(Base):
    """User portfolio tracking balance and total value."""

    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    balance = Column(Float, nullable=False, default=10000.0)
    total_value = Column(Float, nullable=False, default=10000.0)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="portfolios")
    positions = relationship("Position", back_populates="portfolio")
    trades = relationship("Trade", back_populates="portfolio")


class Position(Base):
    """Open or closed trading position."""

    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    symbol = Column(String, nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    average_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, default=0.0)
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    trailing_stop_pct = Column(Float, nullable=True)
    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    exit_date = Column(DateTime, nullable=True)
    exit_reason = Column(String, nullable=True)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    portfolio = relationship("Portfolio", back_populates="positions")


class Trade(Base):
    """Executed trade record."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    symbol = Column(String, nullable=False, index=True)
    side = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    pnl = Column(Float, nullable=True)
    ai_confidence = Column(Float, nullable=True)
    strategy_used = Column(String, nullable=True)
    timestamp = Column(DateTime, default=_utcnow)
    executed_at = Column(DateTime, default=_utcnow)

    portfolio = relationship("Portfolio", back_populates="trades")


class LearningExperience(Base):
    """AI learning experience from trade analysis."""

    __tablename__ = "learning_experiences"

    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    lesson = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_utcnow)


class Alert(Base):
    """System alert notification."""

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    level = Column(String, nullable=False)
    data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    read = Column(Boolean, default=False)


class BacktestResult(Base):
    """Backtest simulation result."""

    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    symbol = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    strategy = Column(String, nullable=False)
    initial_balance = Column(Float, nullable=False)
    final_balance = Column(Float, nullable=True)
    total_return = Column(Float, nullable=True)
    total_return_pct = Column(Float, nullable=True)
    num_trades = Column(Integer, nullable=True)
    win_rate = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=_utcnow)
    completed_at = Column(DateTime, nullable=True)


class TradeRecord(Base):
    """Logs executed trades across all adapters (hexagonal arch)."""

    __tablename__ = "trade_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True)
    side = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    platform = Column(String(30), nullable=False)
    asset_class = Column(SQLEnum(AssetClass), nullable=False)
    executed_at = Column(DateTime, default=_utcnow, index=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert self.quantity > 0, "Quantity must be positive"
        assert self.price >= 0, "Price must be non-negative"


class PositionRecord(Base):
    """Tracks current active portfolio (hexagonal arch)."""

    __tablename__ = "position_records"

    symbol = Column(String(50), primary_key=True)
    platform = Column(String(30), primary_key=True)
    quantity = Column(Float, nullable=False, default=0.0)
    average_entry_price = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, nullable=True)
    last_updated = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class SignalRecord(Base):
    """Audit log of AI-generated trading signals."""

    __tablename__ = "ai_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pair = Column(String(50), nullable=False, index=True)
    action = Column(String(10), nullable=False)
    confidence = Column(Float, nullable=False)
    source = Column(String(50), nullable=False)
    reasoning = Column(String(1000), nullable=True)
    generated_at = Column(DateTime, default=_utcnow, index=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert 0.0 <= self.confidence <= 1.0, "Confidence must be [0.0, 1.0]"


class SystemAuditEvent(Base):
    """Immutable audit trail for critical system events."""

    __tablename__ = "system_audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), default=_utcnow, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    old_state = Column(String(255), nullable=True)
    new_state = Column(String(255), nullable=True)
    actor = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)

