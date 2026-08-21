"""Tests for the /sync-status endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.api import app, update_sync_state


def _reset_sync_state():
    """Reset the module-level sync state to None (simulates fresh start)."""
    import src.api as api_module
    api_module._last_sync_result = None
    api_module._last_sync_at = None
    api_module._next_sync_at = None


class TestSyncStatusBeforeFirstSync:
    def setup_method(self):
        _reset_sync_state()

    def test_returns_200(self):
        client = TestClient(app)
        resp = client.get("/sync-status")
        assert resp.status_code == 200

    def test_last_sync_is_none_before_first_sync(self):
        client = TestClient(app)
        resp = client.get("/sync-status")
        body = resp.json()
        assert body["last_sync"] is None

    def test_next_scheduled_run_is_none_before_sync_starts(self):
        client = TestClient(app)
        resp = client.get("/sync-status")
        body = resp.json()
        assert body["next_scheduled_run"] is None


class TestSyncStatusAfterSync:
    def test_returns_last_sync_result(self):
        update_sync_state({"snapshots_written": 5, "products_seen": 5})
        client = TestClient(app)
        resp = client.get("/sync-status")
        body = resp.json()
        assert body["last_sync"] is not None
        assert body["last_sync"]["result"]["snapshots_written"] == 5
        assert body["last_sync"]["completed_at"] is not None

    def test_returns_next_scheduled_run(self):
        from datetime import datetime, timedelta, timezone
        next_run = datetime.now(timezone.utc) + timedelta(minutes=30)
        update_sync_state({"snapshots_written": 3}, next_run=next_run)
        client = TestClient(app)
        resp = client.get("/sync-status")
        body = resp.json()
        assert body["next_scheduled_run"] is not None
