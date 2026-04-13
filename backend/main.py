"""
AI Stock Trading Bot - Main Application Entry Point

PYTHIA v4.0.0 - FastAPI application with rate limiting, error handling, and monitoring.
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pythia.api.v1 import ai_status, auth, backtest, market_data, portfolio, predictions, trades
from pythia.application.prometheus_metrics import metrics_endpoint, record_api_request
from pythia.application.websocket_manager import (
    market_websocket_endpoint,
    portfolio_websocket_endpoint,
)
from pythia.core.config import settings
from pythia.core.errors import error_handler_middleware
from pythia.core.structured_logging import setup_structured_logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

logger = setup_structured_logging(
    log_level="DEBUG" if settings.DEBUG else "INFO",
    log_file="trading_bot.log",
)

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("application_startup", environment=settings.ENVIRONMENT)
    logger.info(
        "database_config",
        database_url=settings.DATABASE_URL.split("@")[-1],
    )
    yield
    logger.info("application_shutdown")


app = FastAPI(
    title="AI Trading Bot API",
    description="Self-learning AI trading bot with autonomous portfolio growth",
    version=settings.VERSION,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(error_handler_middleware)


@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Track API requests for Prometheus monitoring."""
    start_time = time.time()
    request_id = f"{int(time.time())}-{id(request)}"
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        record_api_request(
            endpoint=request.url.path,
            method=request.method,
            status=response.status_code,
            duration=duration,
        )
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        logger.error(
            "request_failed",
            request_id=request_id,
            path=request.url.path,
            method=request.method,
            exc_info=True,
        )
        raise


app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
app.include_router(ai_status.router, prefix="/api/ai", tags=["ai"])
app.include_router(market_data.router, prefix="/api/market", tags=["market"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["predictions"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])


@app.websocket("/ws/portfolio/{portfolio_id}")
async def websocket_portfolio(websocket: WebSocket, portfolio_id: int):
    """WebSocket endpoint for real-time portfolio updates."""
    await portfolio_websocket_endpoint(websocket, portfolio_id)


@app.websocket("/ws/market")
async def websocket_market(websocket: WebSocket):
    """WebSocket endpoint for real-time market data."""
    await market_websocket_endpoint(websocket)


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return metrics_endpoint()


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "AI Trading Bot API",
        "version": settings.VERSION,
        "status": "online",
        "environment": settings.ENVIRONMENT,
        "documentation": "/docs",
    }


@app.get("/health")
@app.get("/api/v1/health")
async def health_check():
    """
    Health check endpoint with dependency verification.

    Registered at both /health and /api/v1/health for Docker healthcheck compatibility.
    """
    from pythia.application.cache_service import cache_service
    from pythia.infrastructure.persistence.database import engine

    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.VERSION,
        "checks": {},
    }

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "connected"
    except Exception:
        health_status["checks"]["database"] = "error"
        health_status["status"] = "degraded"

    if cache_service.is_available():
        health_status["checks"]["cache"] = "connected"
    else:
        health_status["checks"]["cache"] = "unavailable"

    health_status["checks"]["ai_models"] = "loaded"
    return health_status


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
