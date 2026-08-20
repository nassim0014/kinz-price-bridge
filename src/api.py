"""FastAPI app with a /health endpoint for probeability.

Minimal surface: a single GET /health that returns 200 + JSON status
so the service can be health-checked from Docker/k8s. The sync job
itself runs on a separate APScheduler thread (item 3, not yet
implemented); this API is for orchestration only.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI

app = FastAPI(
    title="kinz-price-bridge",
    description="Bridge service: competitor prices → margin pipeline.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Return 200 + JSON status so probes can verify the service is up."""
    return {
        "status": "ok",
        "service": "kinz-price-bridge",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
