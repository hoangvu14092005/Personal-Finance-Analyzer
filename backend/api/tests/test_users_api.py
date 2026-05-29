"""Tests for current user profile APIs."""
from __future__ import annotations

from app.models.entities import User, UserSettings
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session, select


class TestUsersAuth:
    def test_me_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401


class TestUsersProfile:
    def test_get_current_profile(self, client: TestClient, auth_user: User) -> None:
        response = client.get("/api/v1/users/me")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == auth_user.id
        assert body["email"] == auth_user.email
        assert body["currency"] == "VND"
        assert body["is_active"] is True

    def test_patch_profile_syncs_settings(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        response = client.patch(
            "/api/v1/users/me",
            json={
                "full_name": "Vu Nguyen",
                "currency": "usd",
                "timezone": "Asia/Bangkok",
                "locale": "en-US",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["full_name"] == "Vu Nguyen"
        assert body["currency"] == "USD"
        assert body["timezone"] == "Asia/Bangkok"
        assert body["locale"] == "en-US"

        with Session(engine) as session:
            settings = session.exec(
                select(UserSettings).where(UserSettings.user_id == auth_user.id),
            ).one()
            assert settings.default_currency == "USD"
            assert settings.timezone == "Asia/Bangkok"
            assert settings.locale == "en-US"
            assert settings.number_format_locale == "en-US"

    def test_avatar_upload_is_guarded_until_storage_metadata_exists(
        self,
        client: TestClient,
        auth_user: User,
    ) -> None:
        response = client.post(
            "/api/v1/users/me/avatar",
            files={"file": ("avatar.png", b"png", "image/png")},
        )

        assert response.status_code == 409

    def test_avatar_delete_is_guarded_until_storage_metadata_exists(
        self,
        client: TestClient,
        auth_user: User,
    ) -> None:
        response = client.delete("/api/v1/users/me/avatar")

        assert response.status_code == 409
