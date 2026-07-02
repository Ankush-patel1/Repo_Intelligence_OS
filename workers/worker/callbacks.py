import logging

logger = logging.getLogger(__name__)


def on_task_success(task_name: str, task_id: str) -> None:
    logger.info("Task completed successfully", extra={"task_name": task_name, "task_id": task_id})


def on_task_failure(task_name: str, task_id: str, exc: Exception) -> None:
    logger.error(
        "Task failed", extra={"task_name": task_name, "task_id": task_id, "error": str(exc)}
    )
