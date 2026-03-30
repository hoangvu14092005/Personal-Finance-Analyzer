from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient


def test_logout_clears_auth_cookie() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert "pfa_session=" in response.headers.get("set-cookie", "")
