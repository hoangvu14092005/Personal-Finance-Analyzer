from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient


def test_health_check_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "health-test"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}
    assert response.headers.get("X-Request-ID") == "health-test"
