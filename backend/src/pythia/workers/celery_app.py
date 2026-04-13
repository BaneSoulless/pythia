"""
Celery configuration for Pythia AI Workers.
Handles asynchronous task execution (signal generation, evaluation) to decouple intelligence from execution.
"""

from celery import Celery

from pythia.core.config import settings

# Initialize Celery app
celery_app = Celery(
    "pythia_workers",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1",
)

# Optional configuration, see the application user guide.
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1, # Important for ML tasks that consume lots of memory
)

# Autodiscover tasks in specified packages
celery_app.autodiscover_tasks(["pythia.workers.tasks"])

if __name__ == "__main__":
    celery_app.start()
