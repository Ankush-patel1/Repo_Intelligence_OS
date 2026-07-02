#!/bin/bash
set -e

echo "Starting Celery worker..."
exec celery -A worker.celery_app worker --loglevel=info --concurrency=4
