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


class TestCategoryCreate:
    def test_create_category(self, client: TestClient, auth_user: User) -> None:
        response = client.post(
            "/api/v1/categories",
            json={"name": "Thú cưng", "color": "#123456"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Thú cưng"
        assert body["color"] == "#123456"
        assert body["is_system"] is False
        assert body["user_id"] == auth_user.id

    def test_create_duplicate_name_conflicts(
        self,
        client: TestClient,
        auth_user: User,
        engine: Engine,
    ) -> None:
        _seed_category(engine, name="Food", is_system=True, user_id=None)
        response = client.post("/api/v1/categories", json={"name": "Food"})
        assert response.status_code == 409

    def test_create_requires_auth(self, client: TestClient) -> None:
        # Unauthenticated client (no auth_user fixture).
        fresh = TestClient(client.app)
        response = fresh.post("/api/v1/categories", json={"name": "X"})
        assert response.status_code == 401


class TestCategoryUpdate:
    def test_update_own_category(
        self,
        client: TestClient,
        auth_user: User,
        engine: Engine,
    ) -> None:
        assert auth_user.id is not None
        cat_id = _seed_category(engine, name="Old", is_system=False, user_id=auth_user.id)
        response = client.patch(
            f"/api/v1/categories/{cat_id}",
            json={"name": "New", "color": "#abcdef"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "New"
        assert body["color"] == "#abcdef"

    def test_cannot_update_system_category(
        self,
        client: TestClient,
        auth_user: User,
        engine: Engine,
    ) -> None:
        sys_id = _seed_category(engine, name="Food", is_system=True, user_id=None)
        response = client.patch(f"/api/v1/categories/{sys_id}", json={"name": "Hacked"})
        assert response.status_code == 403

    def test_cannot_update_other_users_category(
        self,
        client: TestClient,
        auth_user: User,
        engine: Engine,
    ) -> None:
        other_id = _seed_user(engine, "other2@example.com")
        cat_id = _seed_category(engine, name="Private", is_system=False, user_id=other_id)
        response = client.patch(f"/api/v1/categories/{cat_id}", json={"name": "X"})
        assert response.status_code == 404


class TestCategoryDelete:
    def test_delete_own_category(
        self,
        client: TestClient,
        auth_user: User,
        engine: Engine,
    ) -> None:
        assert auth_user.id is not None
        cat_id = _seed_category(engine, name="ToDelete", is_system=False, user_id=auth_user.id)
        response = client.delete(f"/api/v1/categories/{cat_id}")
        assert response.status_code == 204

        # Không còn trong list.
        listing = client.get("/api/v1/categories").json()["items"]
        assert all(item["id"] != cat_id for item in listing)

    def test_delete_unsets_transaction_category(
        self,
        client: TestClient,
        auth_user: User,
        engine: Engine,
    ) -> None:
        from datetime import date
        from decimal import Decimal

        from app.models.entities import Transaction

        assert auth_user.id is not None
        cat_id = _seed_category(engine, name="Temp", is_system=False, user_id=auth_user.id)
        with Session(engine) as session:
            tx = Transaction(
                user_id=auth_user.id,
                category_id=cat_id,
                amount=Decimal("1000"),
                transaction_date=date(2026, 5, 1),
            )
            session.add(tx)
            session.commit()
            session.refresh(tx)
            tx_id = tx.id

        response = client.delete(f"/api/v1/categories/{cat_id}")
        assert response.status_code == 204

        with Session(engine) as session:
            tx = session.get(Transaction, tx_id)
            assert tx is not None
            assert tx.category_id is None

    def test_cannot_delete_system_category(
        self,
        client: TestClient,
        auth_user: User,
        engine: Engine,
    ) -> None:
        sys_id = _seed_category(engine, name="Food", is_system=True, user_id=None)
        response = client.delete(f"/api/v1/categories/{sys_id}")
        assert response.status_code == 403
