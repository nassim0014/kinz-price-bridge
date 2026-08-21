"""FastAPI app with /health and /sync-status endpoints.

- GET /health: 200 + JSON for probes (Docker/k8s health checks).
- GET /sync-status: returns the last sync result + next scheduled run,
  so operators can check if the bridge is syncing without reading logs.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI

app = FastAPI(
    title="kinz-price-bridge",
    description="Bridge service: competitor prices → margin pipeline.",
    version="0.1.0",
)

# In-memory state — updated by the sync job. Persisted to the DB in a
# future iteration; for now this is sufficient for the /sync-status endpoint
# to return something useful within a single process lifetime.
_last_sync_result: dict | None = None
_last_sync_at: datetime | None = None
_next_sync_at: datetime | None = None


def update_sync_state(result: dict, next_run: datetime | None = None) -> None:
    """Called by the sync job to record the last result + next scheduled run."""
    global _last_sync_result, _last_sync_at, _next_sync_at
    _last_sync_result = result
    _last_sync_at = datetime.now(timezone.utc)
    _next_sync_at = next_run


@app.get("/health")
def health() -> dict[str, str]:
    """Return 200 + JSON status so probes can verify the service is up."""
    return {
        "status": "ok",
        "service": "kinz-price-bridge",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/sync-status")
def sync_status() -> dict:
    """Return the last sync result + next scheduled run.

    If no sync has run yet (fresh start), last_sync is null.
    """
    return {
        "last_sync": {
            "result": _last_sync_result,
            "completed_at": _last_sync_at.isoformat() if _last_sync_at else None,
        }
        if _last_sync_at
        else None,
        "next_scheduled_run": _next_sync_at.isoformat() if _next_sync_at else None,
    }
