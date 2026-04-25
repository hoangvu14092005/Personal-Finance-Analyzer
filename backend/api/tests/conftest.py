"""Shared pytest fixtures cho backend API tests.

Cung cap:
- `engine`: SQLite in-memory engine duy nhat tao 1 lan/test session.
- `db_session`: Session SQLModel reset truoc moi test, override vao app.
- `client`: TestClient FastAPI da gan dependency override.
- `auth_user`: User test da seed san trong DB voi cookie auth da set.
"""
from __future__ import annotations

from collections.abc import Generator

import pytest
from app.core.database import get_session
from app.core.security import create_access_token
from app.main import app
from app.models.entities import User
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture(scope="session")
def engine() -> Engine:
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture(autouse=True)
def _reset_database(engine: Engine) -> Generator[None, None, None]:
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine: Engine) -> Generator[TestClient, None, None]:
    def _override_session() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _override_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def auth_user(engine: Engine, client: TestClient) -> User:
    """Seed user va set cookie auth len client."""
    with Session(engine) as session:
        user = User(
            email="tester@example.com",
            password_hash="hashed",
            currency="VND",
            timezone="Asia/Ho_Chi_Minh",
            locale="vi-VN",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    if user.id is None:
        raise AssertionError("Seeded user must have an id")

    token = create_access_token(user_id=user.id, email=user.email)
    client.cookies.set("pfa_session", token)
    return user
