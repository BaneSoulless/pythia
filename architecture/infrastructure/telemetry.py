"""
Infrastructure Layer - Deep Observability
Instrumentation: Prometheus Metrics & OpenTelemetry Traces
"""
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
import functools
import logging

logger = logging.getLogger("Telemetry")

# --- METRIC DEFINITIONS ---

# Latency Buckets (Exponential)
LATENCY_BUCKETS = (0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)

# Counters
TICK_COUNTER = Counter('core_ticks_total', 'Total market data ticks processed', ['symbol'])
ORDER_COUNTER = Counter('core_orders_total', 'Total orders generated', ['side', 'type'])
ERROR_COUNTER = Counter('core_errors_total', 'Total system errors', ['module', 'error_type'])

# Gauges
CANDLE_BUFFER_SIZE = Gauge('mem_candle_buffer_size', 'Current size of candle buffer', ['symbol'])
MEMORY_USAGE = Gauge('sys_memory_usage_bytes', 'Process memory usage')
CPU_USAGE = Gauge('sys_cpu_usage_percent', 'Process CPU usage')

# Histograms
INFERENCE_LATENCY = Histogram('ai_inference_duration_seconds', 'Time spent in model inference', buckets=LATENCY_BUCKETS)
DATA_LATENCY = Histogram('net_data_feed_latency_seconds', 'Time delta between candle timestamp and ingest', buckets=LATENCY_BUCKETS)

class MetricsServer:
    _server_started = False

    @staticmethod
    def start(port: int = 9090):
        if not MetricsServer._server_started:
            try:
                start_http_server(port)
                MetricsServer._server_started = True
                logger.info(f"Prometheus Metrics Exporter LIVE on port {port}")
            except Exception as e:
                logger.error(f"Failed to start Metrics Server: {e}")

# --- DECORATORS ---

def measure_inference(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_t = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start_t
            INFERENCE_LATENCY.observe(duration)
            return result
        except Exception as e:
            ERROR_COUNTER.labels(module='inference', error_type=type(e).__name__).inc()
            raise
    return wrapper

def record_tick(symbol: str, timestamp: float):
    TICK_COUNTER.labels(symbol=symbol).inc()
    latency = time.time() - (timestamp / 1000.0) # Binance uses ms
    DATA_LATENCY.observe(max(0, latency))
