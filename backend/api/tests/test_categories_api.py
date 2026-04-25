"""Integration tests cho `GET /api/v1/categories` (Phase 3.4 / 3.6 supporting M4)."""
from __future__ import annotations

from app.core.security import create_access_token
from app.models.entities import Category, User
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session


def _seed_category(
    engine: Engine,
    *,
    name: str,
    is_system: bool,
    user_id: int | None,
    color: str | None = None,
) -> int:
    with Session(engine) as session:
        category = Category(
            name=name,
            is_system=is_system,
            user_id=user_id,
            color=color,
        )
        session.add(category)
        session.commit()
        session.refresh(category)
        if category.id is None:
            raise AssertionError("Category id missing")
        return category.id


def _seed_user(engine: Engine, email: str) -> int:
    with Session(engine) as session:
        user = User(email=email, password_hash="hashed")
        session.add(user)
        session.commit()
        session.refresh(user)
        if user.id is None:
            raise AssertionError("User id missing")
        return user.id


def test_list_categories_returns_system_and_user_owned_only(
    client: TestClient,
    auth_user: User,
    engine: Engine,
) -> None:
    if auth_user.id is None:
        raise AssertionError("auth_user must have id")

    other_user_id = _seed_user(engine, "other@example.com")

    food_id = _seed_category(engine, name="Food", is_system=True, user_id=None)
    transport_id = _seed_category(engine, name="Transport", is_system=True, user_id=None)
    custom_my_id = _seed_category(engine, name="Custom", is_system=False, user_id=auth_user.id)
    # Category của user khác — không được trả về.
    _seed_category(engine, name="OtherUserCat", is_system=False, user_id=other_user_id)

    response = client.get("/api/v1/categories")
    assert response.status_code == 200

    payload = response.json()
    items = payload["items"]
    returned_ids = {item["id"] for item in items}
    assert food_id in returned_ids
    assert transport_id in returned_ids
    assert custom_my_id in returned_ids
    # Đảm bảo không leak category của user khác.
    assert all(item["name"] != "OtherUserCat" for item in items)


def test_list_categories_orders_system_first_then_alpha(
    client: TestClient,
    auth_user: User,
    engine: Engine,
) -> None:
    if auth_user.id is None:
        raise AssertionError("auth_user must have id")

    _seed_category(engine, name="Zoo", is_system=True, user_id=None)
    _seed_category(engine, name="Apple", is_system=True, user_id=None)
    _seed_category(engine, name="Banana", is_system=False, user_id=auth_user.id)
    _seed_category(engine, name="Avocado", is_system=False, user_id=auth_user.id)

    response = client.get("/api/v1/categories")
    assert response.status_code == 200

    items = response.json()["items"]
    # Expected order: system trước (Apple, Zoo), rồi user (Avocado, Banana).
    names = [item["name"] for item in items]
    assert names == ["Apple", "Zoo", "Avocado", "Banana"]


def test_list_categories_empty_when_no_seeds(
    client: TestClient,
    auth_user: User,
) -> None:
    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_list_categories_response_schema(
    client: TestClient,
    auth_user: User,
    engine: Engine,
) -> None:
    if auth_user.id is None:
        raise AssertionError("auth_user must have id")

    _seed_category(
        engine,
        name="Food",
        is_system=True,
        user_id=None,
        color="#ff0000",
    )

    response = client.get("/api/v1/categories")
    assert response.status_code == 200

    items = response.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert set(item.keys()) == {
        "id",
        "name",
        "color",
        "is_system",
        "user_id",
        "created_at",
    }
    assert item["color"] == "#ff0000"
    assert item["is_system"] is True
    assert item["user_id"] is None


def test_list_categories_unauthenticated_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/categories")
    assert response.status_code == 401


def test_list_categories_invalid_token_returns_401(
    client: TestClient,
    engine: Engine,
) -> None:
    # Token reference đến user không tồn tại trong DB.
    token = create_access_token(user_id=99999, email="ghost@example.com")
    client.cookies.set("pfa_session", token)
    response = client.get("/api/v1/categories")
    assert response.status_code == 401
