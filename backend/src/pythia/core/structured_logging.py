"""
Structured logging configuration using structlog.

Provides JSON-formatted logs with structured data for better searchability and monitoring.
"""
import logging
import sys
from pathlib import Path
import structlog
from structlog.stdlib import LoggerFactory

def setup_structured_logging(log_level: str='INFO', log_file: str='trading_bot.log'):
    """
    Configure structured logging with JSON output.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
    """
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    structlog.configure(processors=[structlog.contextvars.merge_contextvars, structlog.processors.add_log_level, structlog.processors.StackInfoRenderer(), structlog.dev.set_exc_info, structlog.processors.TimeStamper(fmt='iso', utc=True), structlog.processors.JSONRenderer()], wrapper_class=structlog.make_filtering_bound_logger(logging.NOTSET), context_class=dict, logger_factory=LoggerFactory(), cache_logger_on_first_use=False)
    logging.basicConfig(format='%(message)s', stream=sys.stdout, level=getattr(logging, log_level.upper()))
    file_handler = logging.FileHandler(log_dir / log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(message)s'))
    logging.getLogger().addHandler(file_handler)
    return structlog.get_logger()

def get_logger(name: str=None):
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
'\nfrom pythia.core.structured_logging import get_logger\n\nlogger = get_logger(__name__)\n\n# Simple log\nlogger.info("application_started")\n\n# Structured log with context\nlogger.info(\n    "trade_executed",\n    symbol="AAPL",\n    side="buy",\n    quantity=10,\n    price=150.0,\n    user_id=123,\n    portfolio_id=1\n)\n\n# Error with exception\ntry:\n    risky_operation()\nexcept Exception as e:\n    logger.error(\n        "operation_failed",\n        operation="risky_operation",\n        error=str(e),\n        exc_info=True\n    )\n\n# With additional context\nlogger = logger.bind(request_id="abc-123", user_id=456)\nlogger.info("processing_request")  # Will include request_id and user_id\n'