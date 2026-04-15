"""
CQRS Pattern Abstractions
SOTA 2026 Architectural Standard

Separates Command (Write) and Query (Read) responsibilities.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

ResultT = TypeVar("ResultT")
CommandT = TypeVar("CommandT", bound="Command")
QueryT = TypeVar("QueryT", bound="Query")


class Command(ABC):  # noqa: B024
    """Base class for all commands (Write operations)."""


class Query(Generic[ResultT], ABC):
    """Base class for all queries (Read operations)."""


class CommandHandler(Generic[CommandT], ABC):
    @abstractmethod
    async def handle(self, command: Command) -> Any:
        pass


class QueryHandler(Generic[QueryT, ResultT], ABC):
    @abstractmethod
    async def handle(self, query: Query) -> ResultT:
        pass


class Mediator:
    """
    Central mediator to route commands and queries to their handlers.
    (Simplified implementation)
    """

    def __init__(self):
        self._command_handlers: dict[type[Command], CommandHandler] = {}
        self._query_handlers: dict[type[Query], QueryHandler] = {}

    def register_command(self, command_type: type[Command], handler: CommandHandler):
        self._command_handlers[command_type] = handler

    def register_query(self, query_type: type[Query], handler: QueryHandler):
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
