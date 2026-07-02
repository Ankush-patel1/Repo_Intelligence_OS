#!/bin/bash
set -e

echo "Running linters..."

echo "Backend (ruff)..."
cd backend
ruff check .
ruff format --check .
cd ..

echo "Frontend (eslint + prettier)..."
cd frontend
npm run lint
npm run format:check
cd ..

echo "Linting complete."
