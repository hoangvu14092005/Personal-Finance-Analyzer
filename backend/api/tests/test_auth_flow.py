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


def test_auth_flow_register_login_me_logout() -> None:
    _reset_database()
    app.dependency_overrides[get_session] = _override_session_factory

    with TestClient(app) as client:
        register = client.post(
            "/api/v1/auth/register",
            json={
                "email": "flow@example.com",
                "password": "StrongPass123",
            },
        )
        assert register.status_code == 201

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "flow@example.com", "password": "StrongPass123"},
        )
        assert login.status_code == 200

        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["email"] == "flow@example.com"

        logout = client.post("/api/v1/auth/logout")
        assert logout.status_code == 204

        me_after_logout = client.get("/api/v1/auth/me")
        assert me_after_logout.status_code == 401

    app.dependency_overrides.clear()
