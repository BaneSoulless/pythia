from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from decimal import Decimal
from app.db.database import Base

class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    portfolios = relationship("Portfolio", back_populates="user")
    backtest_results = relationship("BacktestResult", backref="user")


class Portfolio(Base):
    """Portfolio model - P0-2 FIX: Numeric columns for financial precision"""
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, default="Main Portfolio")
    balance = Column(Numeric(precision=15, scale=2), default=Decimal("10000.00"))
    total_value = Column(Numeric(precision=15, scale=2), default=Decimal("10000.00"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="portfolios")
    positions = relationship("Position", back_populates="portfolio")
    trades = relationship("Trade", back_populates="portfolio")


class Position(Base):
    """Current open positions - P0-2 FIX: Numeric columns for financial precision"""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String, nullable=False, index=True)
    quantity = Column(Numeric(precision=15, scale=6), nullable=False)  # 6 decimals for fractional shares
    average_price = Column(Numeric(precision=15, scale=2), nullable=False)
    current_price = Column(Numeric(precision=15, scale=2), nullable=False)
    unrealized_pnl = Column(Numeric(precision=15, scale=2), default=Decimal("0.00"))
    status = Column(String, default="open")  # open, closed

    # Stop-loss and take-profit
    stop_loss_price = Column(Numeric(precision=15, scale=2), nullable=True)
    take_profit_price = Column(Numeric(precision=15, scale=2), nullable=True)
    entry_price = Column(Numeric(precision=15, scale=2), nullable=True)
    trailing_stop_pct = Column(Numeric(precision=5, scale=4), nullable=True)  # e.g., 0.0200 = 2%
    exit_price = Column(Numeric(precision=15, scale=2), nullable=True)
    exit_date = Column(DateTime, nullable=True)
    exit_reason = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="positions")


class Trade(Base):
    """Trade history - P0-2 FIX: Numeric columns for financial precision"""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    symbol = Column(String, nullable=False, index=True)
    side = Column(String, nullable=False)  # 'buy' or 'sell'
    quantity = Column(Numeric(precision=15, scale=6), nullable=False)
    price = Column(Numeric(precision=15, scale=2), nullable=False)
    commission = Column(Numeric(precision=15, scale=2), default=Decimal("0.00"))
    pnl = Column(Numeric(precision=15, scale=2), nullable=True)  # Realized P&L for sells
    ai_confidence = Column(Float, nullable=True)  # AI confidence kept as Float (not financial)
    strategy_used = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="trades")


class LearningExperience(Base):
    """AI learning experiences for reinforcement learning"""
    __tablename__ = "learning_experiences"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(JSON, nullable=False)  # Market state snapshot
    action = Column(JSON, nullable=False)  # Action taken
    reward = Column(Float, nullable=False)  # Reward received
    next_state = Column(JSON, nullable=False)  # Resulting state
    done = Column(Boolean, default=False)  # Episode ended?
    created_at = Column(DateTime, default=datetime.utcnow)


class ModelCheckpoint(Base):
    """Model training checkpoints"""
    __tablename__ = "model_checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    performance_metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=False)


class Alert(Base):
    """Alert history"""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    level = Column(String, nullable=False)  # info, warning, error, critical
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    read = Column(Boolean, default=False)


class BacktestResult(Base):
    """Backtest results storage"""
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
    status = Column(String, default="pending")  # pending, running, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
