#!/bin/sh
set -e

echo "Running alembic migrations..."
uv run alembic upgrade head

echo "Starting bot..."
exec uv run python src/main.py