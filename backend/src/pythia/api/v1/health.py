"""Health check endpoint for Pythia v4.0.

Exposes /api/v1/health for container orchestrators (Docker, K8s)
and monitoring systems (Prometheus, Traefik).
"""
import time
import logging
from datetime import datetime
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])

_start_time = time.monotonic()


@router.get("/health")
async def health_check() -> dict:
    """System health check endpoint.

    Returns service status, uptime, and component health.
    Used by Docker HEALTHCHECK, K8s livenessProbe, and Traefik.
    """
    uptime_s = time.monotonic() - _start_time

    services = {
        "api": "healthy",
        "orchestrator": "healthy",
    }

    # Probe Redis connectivity
    try:
        import redis
        r = redis.Redis.from_url("redis://localhost:6379/0", socket_timeout=2)
        r.ping()
        services["redis"] = "healthy"
    except Exception:
        services["redis"] = "unavailable"

    # Probe Prometheus exporter
    try:
        from pythia.infrastructure.monitoring.prometheus_exporter import get_metrics_exporter
        exporter = get_metrics_exporter()
        services["prometheus"] = "healthy" if exporter.server_started else "not_started"
    except Exception:
        services["prometheus"] = "unavailable"

    overall = "healthy" if all(v == "healthy" for v in services.values()) else "degraded"

    return {
        "status": overall,
        "version": "4.0.0",
        "uptime_seconds": round(uptime_s, 1),
        "timestamp": datetime.utcnow().isoformat(),
        "services": services,
    }
