from prometheus_client import Counter, Histogram, Gauge, start_http_server
import logging

logger = logging.getLogger(__name__)

# Arbitrage metrics
arbitrage_opportunities_total = Counter(
    'pythia_arbitrage_opportunities_total',
    'Total arbitrage opportunities detected',
    ['platform_pair']
)

arbitrage_roi_percent = Histogram(
    'pythia_arbitrage_roi_percent',
    'ROI distribution of arbitrage opportunities',
    buckets=[0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
)

# Platform balances
prediction_market_balance_usdc = Gauge(
    'pythia_prediction_market_balance_usdc',
    'Current USDC balance on prediction market platform',
    ['platform']
)

# Trading metrics
prediction_market_trades_total = Counter(
    'pythia_prediction_market_trades_total',
    'Total trades executed on prediction markets',
    ['platform', 'side', 'outcome']
)

# Performance metrics
order_placement_latency_seconds = Histogram(
    'pythia_order_placement_latency_seconds',
    'Time taken to place orders',
    ['platform'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Circuit breaker metrics
circuit_breaker_state = Gauge(
    'pythia_circuit_breaker_state',
    'Circuit breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)',
    ['platform', 'state']
)

circuit_breaker_failures_total = Counter(
    'pythia_circuit_breaker_failures_total',
    'Total circuit breaker failures',
    ['platform']
)

# Market scanning metrics
markets_scanned_total = Counter(
    'pythia_markets_scanned_total',
    'Total prediction markets scanned',
    ['platform']
)

class MetricsExporter:
    '''Prometheus metrics exporter for Pythia prediction markets.'''

    def __init__(self, port: int = 9090):
        self.port = port
        self.server_started = False

    def start(self):
        '''Start Prometheus HTTP server.'''
        if not self.server_started:
            try:
                start_http_server(self.port)
                self.server_started = True
                logger.info("Prometheus metrics server started on port %d", self.port)
            except OSError as exc:
                logger.error("Failed to start Prometheus server: %s", exc)

    def record_arbitrage_opportunity(self, platform_pair: str, roi: float):
        '''Record detected arbitrage opportunity.'''
        arbitrage_opportunities_total.labels(platform_pair=platform_pair).inc()
        arbitrage_roi_percent.observe(roi * 100)

    def update_balance(self, platform: str, balance: float):
        '''Update platform balance.'''
        prediction_market_balance_usdc.labels(platform=platform).set(balance)

    def record_trade(self, platform: str, side: str, outcome: str):
        '''Record executed trade.'''
        prediction_market_trades_total.labels(
            platform=platform,
            side=side,
            outcome=outcome
        ).inc()

    def record_order_latency(self, platform: str, latency_seconds: float):
        '''Record order placement latency.'''
        order_placement_latency_seconds.labels(platform=platform).observe(latency_seconds)

    def update_circuit_breaker_state(self, platform: str, state: str):
        '''Update circuit breaker state.'''
        state_value = {"CLOSED": 0, "OPEN": 1, "HALF_OPEN": 2}.get(state, 0)
        circuit_breaker_state.labels(platform=platform, state=state).set(state_value)

    def record_circuit_breaker_failure(self, platform: str):
        '''Record circuit breaker failure.'''
        circuit_breaker_failures_total.labels(platform=platform).inc()

    def record_markets_scanned(self, platform: str, count: int):
        '''Record number of markets scanned.'''
        markets_scanned_total.labels(platform=platform).inc(count)

# Singleton instance
_metrics_exporter = None

def get_metrics_exporter() -> MetricsExporter:
    global _metrics_exporter
    if _metrics_exporter is None:
        _metrics_exporter = MetricsExporter()
        _metrics_exporter.start()
    return _metrics_exporter
