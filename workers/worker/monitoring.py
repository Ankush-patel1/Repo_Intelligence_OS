import logging

logger = logging.getLogger(__name__)


def check_worker_health() -> dict:
    return {
        "status": "healthy",
        "worker": "rio_worker",
    }
