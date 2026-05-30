"""Tests for audit log APIs."""
from __future__ import annotations

from app.models.entities import User
from fastapi.testclient import TestClient


class TestAuditAuth:
    def test_audit_log_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/audit-log")
        assert response.status_code == 401


class TestAuditLog:
    def test_audit_log_returns_empty_list_before_user_actions(
        self,
        client: TestClient,
        auth_user: User,
    ) -> None:
        response = client.get("/api/v1/audit-log")

        assert response.status_code == 200
        assert response.json() == {"items": []}

    def test_audit_log_returns_account_action_events(
        self,
        client: TestClient,
        auth_user: User,
    ) -> None:
        delete_response = client.post(
            "/api/v1/account/delete-request",
            json={"reason": "cleanup"},
        )
        assert delete_response.status_code == 200

        # Tài khoản đang pending-delete bị chặn khỏi endpoint protected thường
        # (chính sách mới). Hủy yêu cầu xóa để user active trở lại rồi đọc audit.
        cancel_response = client.post("/api/v1/account/delete-request/cancel")
        assert cancel_response.status_code == 200

        response = client.get("/api/v1/audit-log")

        assert response.status_code == 200
        items = response.json()["items"]
        events = [item["event"] for item in items]
        assert "account.delete_requested" in events

        requested = next(
            item for item in items if item["event"] == "account.delete_requested"
        )
        assert requested["actor_user_id"] == auth_user.id
        assert requested["target_type"] == "account"
        assert requested["target_id"] == str(auth_user.id)
        assert requested["metadata"] == {"reason_provided": "True"}

    def test_audit_log_respects_limit(
        self,
        client: TestClient,
        auth_user: User,
    ) -> None:
        ai_response = client.patch(
            "/api/v1/settings/ai",
            json={"auto_generate_insights": False},
        )
        privacy_response = client.patch(
            "/api/v1/settings/privacy",
            json={"raw_prompt_retention_days": 30},
        )
        assert ai_response.status_code == 200
        assert privacy_response.status_code == 200

        response = client.get("/api/v1/audit-log?limit=1")

        assert response.status_code == 200
        assert len(response.json()["items"]) == 1
