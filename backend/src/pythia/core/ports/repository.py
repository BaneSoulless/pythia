"""
Repository protocols for isolating domain logic from infrastructure persistence details.
"""

from contextlib import AbstractContextManager
from typing import Protocol

from pythia.infrastructure.persistence.models import Portfolio, Position, Trade


class IPortfolioRepository(Protocol):
    def get_by_id(self, portfolio_id: int) -> Portfolio | None: ...

    def acquire_lock(self, portfolio_id: int) -> AbstractContextManager[Portfolio]: ...


class ITradeRepository(Protocol):
    def get_open_position_count(self, portfolio_id: int) -> int: ...

    def get_open_position(self, portfolio_id: int, symbol: str) -> Position | None: ...

    def get_all_open_positions(self, portfolio_id: int) -> list[Position]: ...

    def save_position(self, position: Position) -> None: ...

    def save_trade(self, trade: Trade) -> None: ...
