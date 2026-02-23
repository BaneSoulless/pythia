import logging
from prometheus_client import start_http_server, Counter, Histogram, Gauge
from typing import Dict, Any

# Metrics Definitions
GROQ_API_CALLS = Counter(
    'pythia_groq_api_calls_total', 
    'Total number of Groq API calls',
    ['pair', 'status']
)

GROQ_LATENCY = Histogram(
    'pythia_groq_api_latency_seconds',
    'Latency of Groq API calls in seconds',
    ['pair']
)

TRADES_EXECUTED = Counter(
    'pythia_trades_executed_total',
    'Total number of trades executed',
    ['pair', 'action']
)

AI_CONFIDENCE = Gauge(
    'pythia_ai_confidence_score',
    'AI confidence score for the last generated signal',
    ['pair']
)

FREQTRADE_BALANCE = Gauge(
    'pythia_freqtrade_balance_usdt',
    'Current dry-run balance in USDT'
)

def start_metrics_server(port: int = 9090):
    """Start the Prometheus metrics server."""
    start_http_server(port)
    print(f"📈 Prometheus metrics exporter started on port {port}")

class MetricsTracker:
    """Helper class to track metrics across the application."""
    
    @staticmethod
    def track_groq_call(pair: str, status: str, latency: float):
        GROQ_API_CALLS.labels(pair=pair, status=status).inc()
        GROQ_LATENCY.labels(pair=pair).observe(latency)

    @staticmethod
    def track_trade(pair: str, action: str, confidence: float):
        TRADES_EXECUTED.labels(pair=pair, action=action).inc()
        AI_CONFIDENCE.labels(pair=pair).set(confidence)

    @staticmethod
    def update_balance(balance: float):
        FREQTRADE_BALANCE.set(balance)
