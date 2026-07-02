#!/bin/bash
set -e

echo "Running tests..."

echo "Backend tests..."
cd backend
pytest
cd ..

echo "Frontend tests..."
cd frontend
npm test
cd ..

echo "All tests complete."
