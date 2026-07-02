#!/bin/bash
set -e

echo "Setting up development environment..."

# Backend setup
echo "Setting up backend..."
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
cd ..

# Frontend setup
echo "Setting up frontend..."
cd frontend
npm install
cd ..

echo "Setup complete!"
echo "Run 'docker compose up' to start all services."
