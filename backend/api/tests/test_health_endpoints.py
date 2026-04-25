"""Tests cho `/health`, `/health/live`, `/health/ready` (M5).

Trong test environment:
- DB là SQLite in-memory → ping luôn ok.
- Redis local có thể down → mock `check_redis` để control behavior.
- S3 default backend là "local" → trả ok không gọi boto3.
"""
from __future__ import annotations

import pytest
from app.services import health_checks
from app.services.health_checks import CheckResult
from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "api"


def test_health_live_returns_ok(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["service"] == "api"


def test_health_ready_all_ok(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Khi tất cả ping ok → status 200 + status='ok'."""
    async def fake_redis_check(_url: str, timeout: float = 0) -> CheckResult:  # noqa: ARG001
        return CheckResult(name="redis", ok=True)

    monkeypatch.setattr(health_checks, "check_redis", fake_redis_check)

    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    components = {c["name"]: c for c in body["components"]}
    assert components["database"]["status"] == "ok"
    assert components["redis"]["status"] == "ok"
    # storage local backend → ok không có error.
    assert components["storage"]["status"] == "ok"


def test_health_ready_redis_down_returns_503(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_redis_check(_url: str, timeout: float = 0) -> CheckResult:  # noqa: ARG001
        return CheckResult(name="redis", ok=False, error="Connection refused")

    monkeypatch.setattr(health_checks, "check_redis", fake_redis_check)

    response = client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    components = {c["name"]: c for c in body["components"]}
    assert components["redis"]["status"] == "down"
    assert components["redis"]["error"] == "Connection refused"
    assert components["database"]["status"] == "ok"


def test_health_ready_db_down_returns_503(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_redis_check(_url: str, timeout: float = 0) -> CheckResult:  # noqa: ARG001
        return CheckResult(name="redis", ok=True)

    async def fake_db_check(timeout: float = 0) -> CheckResult:  # noqa: ARG001
        return CheckResult(name="database", ok=False, error="connection refused")

    monkeypatch.setattr(health_checks, "check_redis", fake_redis_check)
    monkeypatch.setattr(health_checks, "check_database", fake_db_check)

    response = client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    components = {c["name"]: c for c in body["components"]}
    assert components["database"]["status"] == "down"
