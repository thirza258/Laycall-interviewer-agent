#!/bin/bash
set -e

echo "Running database migrations..."
MAX_RETRIES=30
RETRY_DELAY=2
for i in $(seq 1 $MAX_RETRIES); do
    if alembic upgrade head; then
        echo "Migrations completed successfully."
        break
    fi
    if [ $i -eq $MAX_RETRIES ]; then
        echo "ERROR: Database migrations failed after $MAX_RETRIES attempts."
        exit 1
    fi
    echo "Migration attempt $i failed, retrying in ${RETRY_DELAY}s..."
    sleep $RETRY_DELAY
done

echo "Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
