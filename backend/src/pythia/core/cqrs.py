"""
CQRS Pattern Abstractions
SOTA 2026 Architectural Standard

Separates Command (Write) and Query (Read) responsibilities.
"""

from typing import Generic, TypeVar, Any
from abc import ABC, abstractmethod

TResult = TypeVar("TResult")

class Command(ABC):
    """Base class for all commands (Write operations)."""
    pass

class Query(Generic[TResult], ABC):
    """Base class for all queries (Read operations)."""
    pass

class CommandHandler(Generic[Command], ABC):
    @abstractmethod
    async def handle(self, command: Command) -> Any:
        pass

class QueryHandler(Generic[Query, TResult], ABC):
    @abstractmethod
    async def handle(self, query: Query) -> TResult:
        pass

class Mediator:
    """
    Central mediator to route commands and queries to their handlers.
    (Simplified implementation)
    """
    def __init__(self):
        self._command_handlers = {}
        self._query_handlers = {}

    def register_command(self, command_type, handler: CommandHandler):
        self._command_handlers[command_type] = handler

    def register_query(self, query_type, handler: QueryHandler):
        self._query_handlers[query_type] = handler

    async def send(self, command: Command) -> Any:
        handler = self._command_handlers.get(type(command))
        if not handler:
            raise ValueError(f"No handler registered for command {type(command)}")
        return await handler.handle(command)

    async def query(self, query: Query) -> Any:
        handler = self._query_handlers.get(type(query))
        if not handler:
            raise ValueError(f"No handler registered for query {type(query)}")
        return await handler.handle(query)
