"""Tests for Settings APIs."""
from __future__ import annotations

from app.models.entities import User, UserSettings
from fastapi.testclient import TestClient
from sqlmodel import Session, select


class TestSettingsAuth:
    def test_finance_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/settings/finance")
        assert response.status_code == 401


class TestFinanceSettings:
    def test_get_finance_settings_creates_defaults(
        self,
        client: TestClient,
        auth_user: User,
        db_session: Session,
    ) -> None:
        response = client.get("/api/v1/settings/finance")

        assert response.status_code == 200
        body = response.json()
        assert body["default_currency"] == "VND"
        assert body["timezone"] == "Asia/Ho_Chi_Minh"
        assert body["locale"] == "vi-VN"
        assert body["default_analytics_range"] == "30d"

        settings = db_session.exec(
            select(UserSettings).where(UserSettings.user_id == auth_user.id),
        ).first()
        assert settings is not None

    def test_patch_finance_settings_syncs_user_profile(
        self,
        client: TestClient,
        auth_user: User,
        db_session: Session,
    ) -> None:
        response = client.patch(
            "/api/v1/settings/finance",
            json={
                "default_currency": "usd",
                "timezone": "UTC",
                "locale": "en-US",
                "default_analytics_range": "this_month",
                "budget_month_start_day": 5,
                "number_format_locale": "en-US",
                "show_decimals": True,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["default_currency"] == "USD"
        assert body["timezone"] == "UTC"
        assert body["locale"] == "en-US"
        assert body["default_analytics_range"] == "this_month"
        assert body["budget_month_start_day"] == 5
        assert body["show_decimals"] is True

        db_session.expire_all()
        user = db_session.get(User, auth_user.id)
        assert user is not None
        assert user.currency == "USD"
        assert user.timezone == "UTC"
        assert user.locale == "en-US"

    def test_invalid_default_range_rejected(self, client: TestClient, auth_user: User) -> None:
        response = client.patch(
            "/api/v1/settings/finance",
            json={"default_analytics_range": "yesterday"},
        )

        assert response.status_code == 422


class TestAISettings:
    def test_patch_ai_settings(self, client: TestClient, auth_user: User) -> None:
        response = client.patch(
            "/api/v1/settings/ai",
            json={
                "allow_ai_data_processing": False,
                "auto_generate_insights": False,
                "assistant_use_history": False,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["allow_ai_data_processing"] is False
        assert body["auto_generate_insights"] is False
        assert body["assistant_use_history"] is False


class TestNotificationSettings:
    def test_get_notification_settings_defaults(self, client: TestClient, auth_user: User) -> None:
        response = client.get("/api/v1/settings/notifications")

        assert response.status_code == 200
        body = response.json()
        assert body["email_notifications_enabled"] is True
        assert body["push_notifications_enabled"] is False
        assert body["budget_alerts_enabled"] is True
        assert body["receipt_notifications_enabled"] is True
        assert body["insight_notifications_enabled"] is True

    def test_patch_notification_settings(self, client: TestClient, auth_user: User) -> None:
        response = client.patch(
            "/api/v1/settings/notifications",
            json={
                "email_notifications_enabled": False,
                "budget_alerts_enabled": False,
                "receipt_notifications_enabled": False,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["email_notifications_enabled"] is False
        assert body["budget_alerts_enabled"] is False
        assert body["receipt_notifications_enabled"] is False
        assert body["push_notifications_enabled"] is False
        assert body["insight_notifications_enabled"] is True


class TestPrivacySettings:
    def test_patch_privacy_settings(self, client: TestClient, auth_user: User) -> None:
        response = client.patch(
            "/api/v1/settings/privacy",
            json={
                "receipt_file_retention_days": 180,
                "raw_prompt_retention_days": 30,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["receipt_file_retention_days"] == 180
        assert body["raw_prompt_retention_days"] == 30
