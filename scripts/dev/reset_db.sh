#!/bin/bash
set -e

echo "Resetting database..."
docker compose down -v
docker compose up -d postgres
echo "Waiting for database..."
sleep 5
cd backend
alembic upgrade head
echo "Database reset complete."
