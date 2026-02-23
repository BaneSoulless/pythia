"""
Prometheus Metrics for Monitoring

Exposes trading bot metrics for Prometheus scraping
"""
from prometheus_client import Counter, Gauge, Histogram, Summary, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time
trades_total = Counter('trading_bot_trades_total', 'Total number of trades executed', ['side', 'symbol'])
trade_pnl = Histogram('trading_bot_trade_pnl', 'Profit/Loss per trade', buckets=[-100, -50, -10, -5, 0, 5, 10, 50, 100, 500])
portfolio_value = Gauge('trading_bot_portfolio_value', 'Current portfolio total value', ['portfolio_id'])
portfolio_balance = Gauge('trading_bot_portfolio_balance', 'Current cash balance', ['portfolio_id'])
open_positions = Gauge('trading_bot_open_positions', 'Number of open positions', ['portfolio_id'])
ai_predictions_total = Counter('trading_bot_ai_predictions_total', 'Total AI predictions made', ['action'])
ai_model_confidence = Histogram('trading_bot_ai_confidence', 'AI model confidence scores', buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
ai_training_duration = Summary('trading_bot_ai_training_duration_seconds', 'Time spent training AI model')
ai_epsilon = Gauge('trading_bot_ai_epsilon', 'Current epsilon (exploration rate)', ['model_id'])
api_requests_total = Counter('trading_bot_api_requests_total', 'Total API requests', ['endpoint', 'method', 'status'])
api_request_duration = Histogram('trading_bot_api_request_duration_seconds', 'API request duration', ['endpoint'])
market_data_fetches_total = Counter('trading_bot_market_data_fetches_total', 'Total market data API calls', ['provider', 'status'])
market_data_fetch_duration = Histogram('trading_bot_market_data_fetch_duration_seconds', 'Market data fetch duration', ['provider'])
errors_total = Counter('trading_bot_errors_total', 'Total errors encountered', ['error_type'])
risk_limit_violations = Counter('trading_bot_risk_limit_violations_total', 'Total risk limit violations', ['limit_type'])
min_balance_violations = Counter('trading_bot_min_balance_violations_total', 'Attempted trades below minimum balance')

def metrics_endpoint() -> Response:
    """
    Endpoint to expose Prometheus metrics
    
    Add to FastAPI:
    ```python
    from pythia.application.prometheus_metrics import metrics_endpoint
    
    @app.get("/metrics")
    async def metrics():
        return metrics_endpoint()
    ```
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

def record_trade(symbol: str, side: str, pnl: float=None):
    """Record a trade execution"""
    trades_total.labels(side=side, symbol=symbol).inc()
    if pnl is not None:
        trade_pnl.observe(pnl)

def record_portfolio_metrics(portfolio_id: int, total_value: float, balance: float, positions_count: int):
    """Record portfolio state"""
    portfolio_value.labels(portfolio_id=str(portfolio_id)).set(total_value)
    portfolio_balance.labels(portfolio_id=str(portfolio_id)).set(balance)
    open_positions.labels(portfolio_id=str(portfolio_id)).set(positions_count)

def record_ai_prediction(action: str, confidence: float):
    """Record AI model prediction"""
    ai_predictions_total.labels(action=action).inc()
    ai_model_confidence.observe(confidence)

def record_ai_epsilon(model_id: str, epsilon: float):
    """Record current AI epsilon"""
    ai_epsilon.labels(model_id=model_id).set(epsilon)

def record_api_request(endpoint: str, method: str, status: int, duration: float):
    """Record API request"""
    api_requests_total.labels(endpoint=endpoint, method=method, status=str(status)).inc()
    api_request_duration.labels(endpoint=endpoint).observe(duration)

def record_market_data_fetch(provider: str, status: str, duration: float):
    """Record market data fetch"""
    market_data_fetches_total.labels(provider=provider, status=status).inc()
    market_data_fetch_duration.labels(provider=provider).observe(duration)

def record_error(error_type: str):
    """Record an error"""
    errors_total.labels(error_type=error_type).inc()

def record_risk_violation(limit_type: str):
    """Record risk limit violation"""
    risk_limit_violations.labels(limit_type=limit_type).inc()

def record_min_balance_violation():
    """Record minimum balance violation"""
    min_balance_violations.inc()