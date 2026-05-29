"""Tests for security/session APIs."""
from __future__ import annotations

from app.models.entities import User
from fastapi.testclient import TestClient


class TestSecurityAuth:
    def test_sessions_require_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/security/sessions")
        assert response.status_code == 401


class TestSecuritySessions:
    def test_list_sessions_returns_current_session(
        self,
        client: TestClient,
        auth_user: User,
    ) -> None:
        response = client.get("/api/v1/security/sessions")

        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["id"] == "current"
        assert body["items"][0]["user_id"] == auth_user.id
        assert body["items"][0]["is_current"] is True

    def test_login_history_returns_empty_list_without_login_events(
        self,
        client: TestClient,
        auth_user: User,
    ) -> None:
        response = client.get("/api/v1/security/login-history")

        assert response.status_code == 200
        assert response.json() == {"items": []}

    def test_delete_unknown_session_returns_404(self, client: TestClient, auth_user: User) -> None:
        response = client.delete("/api/v1/security/sessions/not-current")

        assert response.status_code == 404

    def test_delete_current_session_clears_cookie(
        self,
        client: TestClient,
        auth_user: User,
    ) -> None:
        response = client.delete("/api/v1/security/sessions/current")

        assert response.status_code == 204
        assert "pfa_session=" in response.headers.get("set-cookie", "")
