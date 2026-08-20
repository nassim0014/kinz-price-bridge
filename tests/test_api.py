"""Tests for the /health endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.api import app


def test_health_returns_200():
    """The health endpoint must return 200 OK."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_ok_status():
    """The response body must say status=ok."""
    client = TestClient(app)
    response = client.get("/health")
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "kinz-price-bridge"


def test_health_has_timestamp():
    """The response must include an ISO-8601 UTC timestamp."""
    client = TestClient(app)
    response = client.get("/health")
    body = response.json()
    assert "timestamp" in body
    # ISO-8601 UTC: datetime.now(timezone.utc).isoformat() ends with +00:00
    assert body["timestamp"].endswith("+00:00")
