"""
Error codes and custom exceptions for the trading bot.

Provides standardized error handling across all services.
Sanitizes 500 responses to prevent internal detail leakage.
"""

import structlog
from enum import StrEnum
from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


class ErrorCode(StrEnum):
    """Standardized error codes for the trading bot."""

    # Authentication Errors (E1xxx)
    AUTH_INVALID_CREDENTIALS = "E1001"
    AUTH_TOKEN_EXPIRED = "E1002"
    AUTH_TOKEN_INVALID = "E1003"
    AUTH_USER_NOT_FOUND = "E1004"
    AUTH_USER_INACTIVE = "E1005"
    AUTH_REGISTRATION_FAILED = "E1006"

    # Trading Errors (E2xxx)
    TRADE_INSUFFICIENT_BALANCE = "E2001"
    TRADE_INVALID_SYMBOL = "E2002"
    TRADE_POSITION_SIZE_EXCEEDED = "E2003"
    TRADE_RISK_LIMIT_EXCEEDED = "E2004"
    TRADE_EXECUTION_FAILED = "E2005"
    TRADE_INVALID_SIDE = "E2006"
    TRADE_INVALID_QUANTITY = "E2007"
    TRADE_MIN_BALANCE_VIOLATION = "E2008"
    TRADE_LIVE_TRADING_DISABLED = "E2009"

    # Market Data Errors (E3xxx)
    MARKET_API_ERROR = "E3001"
    MARKET_RATE_LIMIT = "E3002"
    MARKET_SYMBOL_NOT_FOUND = "E3003"
    MARKET_DATA_UNAVAILABLE = "E3004"
    MARKET_INVALID_TIMEFRAME = "E3005"

    # Database Errors (E4xxx)
    DB_CONNECTION_ERROR = "E4001"
    DB_CONSTRAINT_VIOLATION = "E4002"
    DB_RECORD_NOT_FOUND = "E4003"
    DB_TRANSACTION_FAILED = "E4004"

    # AI/ML Errors (E5xxx)
    AI_MODEL_NOT_LOADED = "E5001"
    AI_PREDICTION_FAILED = "E5002"
    AI_TRAINING_ERROR = "E5003"
    AI_INVALID_STATE = "E5004"

    # Portfolio Errors (E6xxx)
    PORTFOLIO_NOT_FOUND = "E6001"
    PORTFOLIO_ALREADY_EXISTS = "E6002"
    POSITION_NOT_FOUND = "E6003"
    POSITION_CANNOT_CLOSE = "E6004"

    # Backtesting Errors (E7xxx)
    BACKTEST_INVALID_PARAMS = "E7001"
    BACKTEST_FAILED = "E7002"
    BACKTEST_NOT_FOUND = "E7003"

    # Alert Errors (E8xxx)
    ALERT_SEND_FAILED = "E8001"
    ALERT_INVALID_CHANNEL = "E8002"

    # General Errors (E9xxx)
    VALIDATION_ERROR = "E9001"
    INTERNAL_ERROR = "E9002"
    NOT_IMPLEMENTED = "E9003"
    RATE_LIMIT_EXCEEDED = "E9004"


class TradingBotError(Exception):
    """Base exception for all trading bot errors."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.original_error = original_error
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error_code": self.code,
            "message": self.message,
            "details": self.details,
        }


class AuthenticationError(TradingBotError):
    """Authentication related errors."""


class TradingError(TradingBotError):
    """Trading operation errors."""


class MarketDataError(TradingBotError):
    """Market data retrieval errors."""


class DatabaseError(TradingBotError):
    """Database operation errors."""


class AIError(TradingBotError):
    """AI/ML operation errors."""


class MLGateError(AIError):
    """ML Meta-Labeling gate inference errors."""


class PortfolioError(TradingBotError):
    """Portfolio management errors."""


class BacktestError(TradingBotError):
    """Backtesting errors."""


class AlertError(TradingBotError):
    """Alert system errors."""


class ValidationError(TradingBotError):
    """Input validation errors."""


class ResourceNotFoundError(TradingBotError):
    """Resource not found errors."""


async def error_handler_middleware(request: Request, call_next):
    """Global error handling middleware with sanitized responses."""
    try:
        return await call_next(request)
    except TradingBotError as e:
        logger.warning(
            "trading_bot_error",
            error_code=e.code.value,
            message=e.message,
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=e.to_dict(),
        )
    except Exception:
        logger.error("unhandled_exception", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_code": ErrorCode.INTERNAL_ERROR,
                "message": "An internal error occurred. Please try again later.",
                "details": {},
            },
        )
