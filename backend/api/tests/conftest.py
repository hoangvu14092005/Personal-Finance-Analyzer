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


@pytest.fixture(autouse=True)
def _override_health_engine(
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Force health_checks.check_database dùng test SQLite engine.

    `app.services.health_checks` import `engine` từ `app.core.database` ở
    module load time → bound vào postgres engine production. Test override
    bằng monkeypatch để `/health/ready` ping được test DB."""
    monkeypatch.setattr("app.services.health_checks.engine", engine)


@pytest.fixture(autouse=True)
def _reset_storage_singleton() -> Generator[None, None, None]:
    """Clear `get_storage_service` lru_cache giữa các test.

    `get_storage_service` cache theo `settings.storage_backend` — test có
    thể đổi setting → cần invalidate để pick up backend mới."""
    from app.integrations.storage.factory import get_storage_service

    get_storage_service.cache_clear()
    yield
    get_storage_service.cache_clear()


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
