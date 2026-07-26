#!/bin/sh
set -e

echo "Running alembic migrations..."
uv run alembic upgrade head

echo "Starting bot..."
exec uv run uvicorn main:application --host 0.0.0.0 --port "${BOT_PORT:-5000}" --factory --app-dir src