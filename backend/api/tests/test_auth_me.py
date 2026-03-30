from __future__ import annotations

from app.core.database import get_session
from app.core.security import create_access_token
from app.main import app
from app.models.entities import User
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


def _seed_user() -> User:
    with Session(engine) as session:
        user = User(
            email="me@example.com",
            password_hash="hashed",
            currency="VND",
            timezone="Asia/Ho_Chi_Minh",
            locale="vi-VN",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def test_get_me_with_valid_cookie_returns_profile() -> None:
    _reset_database()
    user = _seed_user()
    app.dependency_overrides[get_session] = _override_session_factory

    if user.id is None:
        raise AssertionError("Seeded user id is required")

    token = create_access_token(user_id=user.id, email=user.email)

    with TestClient(app) as client:
        client.cookies.set("pfa_session", token)
        response = client.get("/api/v1/auth/me")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "me@example.com"


def test_get_me_without_cookie_returns_unauthorized() -> None:
    _reset_database()
    app.dependency_overrides[get_session] = _override_session_factory

    with TestClient(app) as client:
        response = client.get("/api/v1/auth/me")

    app.dependency_overrides.clear()

    assert response.status_code == 401
