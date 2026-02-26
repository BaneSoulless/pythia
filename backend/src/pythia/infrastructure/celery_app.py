"""Celery application configuration for Pythia v4.0.

Defines the Celery app, task autodiscovery, and beat schedule.
Broker: Redis 7.x. Result backend: Redis.
"""
import os
import logging
from celery import Celery

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

app = Celery(
    "pythia",
    broker=REDIS_URL,
    backend=RESULT_BACKEND,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    task_queues={
        "default": {"exchange": "default", "routing_key": "default"},
        "pm_scanner": {"exchange": "pm", "routing_key": "pm.scan"},
        "trading": {"exchange": "trading", "routing_key": "trading.execute"},
        "ai_signals": {"exchange": "ai", "routing_key": "ai.signal"},
    },
    task_routes={
        "pythia.infrastructure.tasks.scan_prediction_markets": {"queue": "pm_scanner"},
        "pythia.infrastructure.tasks.execute_multi_asset_trade": {"queue": "trading"},
        "pythia.infrastructure.tasks.generate_ai_signal": {"queue": "ai_signals"},
    },
    beat_schedule={
        "pm-arbitrage-scan-5min": {
            "task": "pythia.infrastructure.tasks.scan_prediction_markets",
            "schedule": 300.0,  # every 5 minutes
            "options": {"queue": "pm_scanner"},
        },
    },
)

app.autodiscover_tasks(["pythia.infrastructure"])
