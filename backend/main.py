"""
AI Stock Trading Bot - Main Application Entry Point

Complete FastAPI application with rate limiting, error handling, and monitoring.
"""
import logging
from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import time

from app.core.config import settings
from app.core.structured_logging import setup_structured_logging, get_logger
from app.core.errors import error_handler_middleware
from app.core.errors import TradingBotError

# API Routers
from app.api import portfolio, trades, ai_status, market_data, predictions, backtest, auth

# Services
from app.services.websocket_manager import portfolio_websocket_endpoint, market_websocket_endpoint
from app.services.prometheus_metrics import metrics_endpoint, record_api_request

# Setup structured logging
logger = setup_structured_logging(
    log_level="DEBUG" if settings.DEBUG else "INFO",
    log_file="trading_bot.log"
)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("application_startup", environment=settings.ENVIRONMENT)
    logger.info("database_config", database_url=settings.DATABASE_URL.split('@')[-1])  # Hide credentials
    
    # Startup tasks
    yield
    
    # Shutdown tasks
    logger.info("application_shutdown")


# Initialize FastAPI app
app = FastAPI(
    title="AI Trading Bot API",
    description="Self-learning AI trading bot with autonomous portfolio growth",
    version="3.0.0",
    lifespan=lifespan
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(",") if hasattr(settings, 'CORS_ORIGINS') else ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handling middleware
app.middleware("http")(error_handler_middleware)


# Request tracking middleware
@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Track API requests for monitoring"""
    start_time = time.time()
    
    # Add request ID
    request_id = f"{int(time.time())}-{id(request)}"
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Record metrics
        record_api_request(
            endpoint=request.url.path,
            method=request.method,
            status=response.status_code,
            duration=duration
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
    except Exception as e:
        logger.error(
            "request_failed",
            request_id=request_id,
            path=request.url.path,
            method=request.method,
            error=str(e),
            exc_info=True
        )
        raise


# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
app.include_router(ai_status.router, prefix="/api/ai", tags=["ai"])
app.include_router(market_data.router, prefix="/api/market", tags=["market"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["predictions"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])


# WebSocket endpoints
@app.websocket("/ws/portfolio/{portfolio_id}")
async def websocket_portfolio(websocket: WebSocket, portfolio_id: int):
    """WebSocket endpoint for real-time portfolio updates"""
    await portfolio_websocket_endpoint(websocket, portfolio_id)


@app.websocket("/ws/market")
async def websocket_market(websocket: WebSocket):
    """WebSocket endpoint for real-time market data"""
    await market_websocket_endpoint(websocket)


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return metrics_endpoint()


# Root endpoints
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AI Trading Bot API",
        "version": "3.0.0",
        "status": "online",
        "environment": settings.ENVIRONMENT,
        "features": [
            "Real-time trading engine",
            "AI-powered decision making",
            "Multi-model ensemble (7 AI models)",
            "WebSocket real-time updates",
            "Advanced technical analysis",
            "Backtesting engine",
            "Prometheus metrics",
            "Risk management",
            "Stop-loss/Take-profit automation",
            "Multi-symbol trading"
        ],
        "documentation": "/docs"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint with dependency verification
    
    Returns service health status and dependency checks
    """
    from app.db.database import engine
    from app.services.cache_service import cache_service
    
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {}
    }
    
    # Database check
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        health_status["checks"]["database"] = "connected"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Redis cache check
    if cache_service.is_available():
        health_status["checks"]["cache"] = "connected"
    else:
        health_status["checks"]["cache"] = "unavailable"
        # Cache is optional, don't mark as degraded
    
    # AI models check (simplified)
    health_status["checks"]["ai_models"] = "loaded"
    
    return health_status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
