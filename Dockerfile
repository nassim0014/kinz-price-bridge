# =============================================================================
# kinz-price-bridge — Dockerfile
# =============================================================================
# Single-stage build on Python 3.12-slim. Runs the sync scheduler in
# --watch mode by default (every SYNC_INTERVAL_MINUTES minutes).
#
# The image is intentionally minimal: no browser, no Airflow, no
# dashboard. Just the FastAPI app + the sync scheduler.
# =============================================================================

FROM python:3.12-slim

# Don't write .pyc files (saves space, avoids stale-cache bugs in containers)
ENV PYTHONDONTWRITEBYTECODE=1
# Unbuffered stdout so logs appear immediately in docker logs
ENV PYTHONUNBUFFERED=1
# Default sync interval (minutes) — override at runtime
ENV SYNC_INTERVAL_MINUTES=30

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Create a non-root user to run the app
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

# Default command: run the sync scheduler in watch mode
# Override with: docker run kinz-price-bridge uvicorn src.api:app --host 0.0.0.0 --port 8000
CMD ["python", "-m", "scripts.run_sync", "--watch"]
