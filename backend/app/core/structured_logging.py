"""
Structured logging configuration using structlog.

Provides JSON-formatted logs with structured data for better searchability and monitoring.
"""
import logging
import sys
from pathlib import Path
import structlog
from structlog.stdlib import LoggerFactory


def setup_structured_logging(log_level: str = "INFO", log_file: str = "trading_bot.log"):
    """
    Configure structured logging with JSON output.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
    """
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.NOTSET),
        context_class=dict,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=False
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )
    
    # Add file handler
    file_handler = logging.FileHandler(log_dir / log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(message)s'))
    logging.getLogger().addHandler(file_handler)
    
    return structlog.get_logger()


def get_logger(name: str = None):
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Structured logger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("trade_executed", symbol="AAPL", quantity=10, price=150.0)
    """
    return structlog.get_logger(name)


# Example usage patterns
"""
from app.core.structured_logging import get_logger

logger = get_logger(__name__)

# Simple log
logger.info("application_started")

# Structured log with context
logger.info(
    "trade_executed",
    symbol="AAPL",
    side="buy",
    quantity=10,
    price=150.0,
    user_id=123,
    portfolio_id=1
)

# Error with exception
try:
    risky_operation()
except Exception as e:
    logger.error(
        "operation_failed",
        operation="risky_operation",
        error=str(e),
        exc_info=True
    )

# With additional context
logger = logger.bind(request_id="abc-123", user_id=456)
logger.info("processing_request")  # Will include request_id and user_id
"""
