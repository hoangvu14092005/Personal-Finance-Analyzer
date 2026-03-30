from __future__ import annotations

from app.core.database import get_session
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def _reset_database() -> None:
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def _override_session_factory() -> Session:
    with Session(engine) as session:
        yield session


def test_register_success() -> None:
    _reset_database()
    app.dependency_overrides[get_session] = _override_session_factory

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "register@example.com",
                "password": "StrongPass123",
                "currency": "VND",
                "timezone": "Asia/Ho_Chi_Minh",
                "locale": "vi-VN",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["user"]["email"] == "register@example.com"


def test_register_duplicate_email_returns_conflict() -> None:
    _reset_database()
    app.dependency_overrides[get_session] = _override_session_factory

    payload = {
        "email": "duplicate@example.com",
        "password": "StrongPass123",
        "currency": "VND",
        "timezone": "Asia/Ho_Chi_Minh",
        "locale": "vi-VN",
    }

    with TestClient(app) as client:
        first = client.post("/api/v1/auth/register", json=payload)
        second = client.post("/api/v1/auth/register", json=payload)

    app.dependency_overrides.clear()

    assert first.status_code == 201
    assert second.status_code == 409


def test_register_without_profile_fields_uses_defaults() -> None:
    _reset_database()
    app.dependency_overrides[get_session] = _override_session_factory

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "default-profile@example.com",
                "password": "StrongPass123",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()["user"]
    assert payload["currency"] == "VND"
    assert payload["timezone"] == "Asia/Ho_Chi_Minh"
    assert payload["locale"] == "vi-VN"
