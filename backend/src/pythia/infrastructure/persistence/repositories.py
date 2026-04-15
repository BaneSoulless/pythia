"""
SQLAlchemy implementations of core repository protocols.
"""

from contextlib import AbstractContextManager, contextmanager

from pythia.core.errors import ErrorCode, TradingError
from pythia.core.ports.repository import IPortfolioRepository, ITradeRepository
from pythia.core.structured_logging import get_logger
from pythia.infrastructure.persistence.models import Portfolio, Position, Trade
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = get_logger(__name__)


class SqlAlchemyPortfolioRepository(IPortfolioRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, portfolio_id: int) -> Portfolio | None:
        return self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()

    @contextmanager
    def acquire_lock(self, portfolio_id: int) -> AbstractContextManager[Portfolio]:
        try:
            portfolio = self.db.execute(
                select(Portfolio)
                .where(Portfolio.id == portfolio_id)
                .with_for_update(nowait=True)
            ).scalar_one()
            yield portfolio
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error("trade_lock_failed", portfolio_id=portfolio_id, error=str(e))
            raise TradingError(
                code=ErrorCode.DB_TRANSACTION_FAILED,
                message="Concurrent trade detected - please retry",
                details={"portfolio_id": portfolio_id},
            ) from e


class SqlAlchemyTradeRepository(ITradeRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_open_position_count(self, portfolio_id: int) -> int:
        return (
            self.db.query(Position)
            .filter(Position.portfolio_id == portfolio_id, Position.status == "open")
            .count()
        )

    def get_open_position(self, portfolio_id: int, symbol: str) -> Position | None:
        return (
            self.db.query(Position)
            .filter(
                Position.portfolio_id == portfolio_id,
                Position.symbol == symbol,
                Position.status == "open",
            )
            .first()
        )

    def get_all_open_positions(self, portfolio_id: int) -> list[Position]:
        return (
            self.db.query(Position)
            .filter(Position.portfolio_id == portfolio_id, Position.status == "open")
            .all()
        )

    def save_position(self, position: Position) -> None:
        self.db.add(position)

    def save_trade(self, trade: Trade) -> None:
        self.db.add(trade)
