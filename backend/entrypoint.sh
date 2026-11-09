#!/bin/sh
set -e

# Apply database migrations, then start the API server.
echo "Running database migrations..."
alembic upgrade head

echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
