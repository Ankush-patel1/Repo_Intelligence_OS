#!/bin/bash
set -e

echo "Waiting for database..."
until pg_isready -h postgres -U rio 2>/dev/null; do
  sleep 1
done
echo "Database is ready."

echo "Running migrations..."
cd /app/backend
alembic -c alembic/alembic.ini upgrade head 2>/dev/null || echo "No migrations to run."

echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
