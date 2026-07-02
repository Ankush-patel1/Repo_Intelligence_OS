import os

from celery import Celery

REDIS_URL = os.getenv("RIO_REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "rio_worker",
    broker=os.getenv("RIO_CELERY_BROKER_URL", REDIS_URL),
    backend=os.getenv("RIO_CELERY_RESULT_BACKEND", REDIS_URL),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=86400,
)
