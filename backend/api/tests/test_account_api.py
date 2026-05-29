"""Tests for account lifecycle APIs."""
from __future__ import annotations

from app.models.entities import User
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session


class TestAccountAuth:
    def test_delete_request_requires_auth(self, client: TestClient) -> None:
        response = client.post("/api/v1/account/delete-request", json={})
        assert response.status_code == 401


class TestAccountDeleteRequest:
    def test_request_and_cancel_account_deletion(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        request = client.post(
            "/api/v1/account/delete-request",
            json={"reason": "testing"},
        )

        assert request.status_code == 200
        requested = request.json()
        assert requested["status"] == "pending"
        assert requested["requested_at"] is not None
        assert requested["scheduled_at"] is not None

        with Session(engine) as session:
            user = session.get(User, auth_user.id)
            assert user is not None
            assert user.account_deletion_requested_at is not None

        cancel = client.post("/api/v1/account/delete-request/cancel")

        assert cancel.status_code == 200
        cancelled = cancel.json()
        assert cancelled["status"] == "cancelled"
        assert cancelled["requested_at"] is None
        assert cancelled["scheduled_at"] is None
        assert cancelled["cancelled_at"] is not None
