"""Tests for the health/readiness endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app_env"] == "test"
    assert body["version"] == "0.1.0"


def test_health_sets_request_id_header(client: TestClient) -> None:
    resp = client.get("/health")
    assert "x-request-id" in resp.headers


def test_ready_returns_ready(client: TestClient) -> None:
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"
