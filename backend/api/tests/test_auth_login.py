from __future__ import annotations

from app.core.database import get_session
from app.main import app
from app.models.entities import User
from app.services.password_service import hash_password
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


def _seed_user() -> None:
    with Session(engine) as session:
        session.add(
            User(
                email="login@example.com",
                password_hash=hash_password("StrongPass123"),
                currency="VND",
                timezone="Asia/Ho_Chi_Minh",
                locale="vi-VN",
            )
        )
        session.commit()


def test_login_success_sets_cookie() -> None:
    _reset_database()
    _seed_user()
    app.dependency_overrides[get_session] = _override_session_factory

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": "StrongPass123"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "login@example.com"
    assert "pfa_session=" in response.headers.get("set-cookie", "")


def test_login_wrong_password_returns_unauthorized() -> None:
    _reset_database()
    _seed_user()
    app.dependency_overrides[get_session] = _override_session_factory

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": "Wrong12345"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 401
