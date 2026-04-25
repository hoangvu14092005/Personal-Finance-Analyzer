"""Integration tests cho Phase 3 Transaction APIs."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.models.entities import (
    Category,
    ReceiptUpload,
    Transaction,
    User,
    UserMerchantMapping,
)
from fastapi.testclient import TestClient
from pfa_shared.enums import ReceiptStatus
from sqlalchemy.engine import Engine
from sqlmodel import Session, select


def _seed_user(engine: Engine, email: str = "other@example.com") -> User:
    with Session(engine) as session:
        user = User(
            email=email,
            password_hash="hashed",
            currency="VND",
            timezone="Asia/Ho_Chi_Minh",
            locale="vi-VN",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def _seed_category(
    engine: Engine,
    name: str,
    user_id: int | None = None,
    is_system: bool = False,
) -> Category:
    with Session(engine) as session:
        category = Category(
            user_id=user_id,
            name=name,
            is_system=is_system,
        )
        session.add(category)
        session.commit()
        session.refresh(category)
        return category


def _seed_receipt(engine: Engine, user_id: int) -> ReceiptUpload:
    with Session(engine) as session:
        receipt = ReceiptUpload(
            user_id=user_id,
            file_name="receipt.jpg",
            content_type="image/jpeg",
            file_size_bytes=10,
            storage_key=f"{user_id}/receipt.jpg",
            status=ReceiptStatus.READY.value,
        )
        session.add(receipt)
        session.commit()
        session.refresh(receipt)
        return receipt


# -------------------- POST /transactions --------------------


def test_create_transaction_manual_entry_success(
    client: TestClient,
    auth_user: User,
) -> None:
    response = client.post(
        "/api/v1/transactions",
        json={
            "amount": "125000.00",
            "currency": "vnd",
            "transaction_date": "2026-04-01",
            "merchant_name": "  Mock Mart  ",
            "note": "Lunch",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user_id"] == auth_user.id
    assert body["amount"] == "125000.00"
    assert body["currency"] == "VND"
    assert body["merchant_name"] == "Mock Mart"
    assert body["category_id"] is None
    assert body["receipt_upload_id"] is None


def test_create_transaction_zero_amount_returns_validation_error(
    client: TestClient,
    auth_user: User,
) -> None:
    response = client.post(
        "/api/v1/transactions",
        json={
            "amount": "0",
            "currency": "VND",
            "transaction_date": "2026-04-01",
        },
    )
    assert response.status_code == 422


def test_create_transaction_unauthenticated_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/v1/transactions",
        json={
            "amount": "10000",
            "currency": "VND",
            "transaction_date": "2026-04-01",
        },
    )
    assert response.status_code == 401


def test_create_transaction_with_unowned_receipt_returns_404(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    other_user = _seed_user(engine, email="stranger@example.com")
    assert other_user.id is not None
    receipt = _seed_receipt(engine, user_id=other_user.id)

    response = client.post(
        "/api/v1/transactions",
        json={
            "amount": "10000",
            "currency": "VND",
            "transaction_date": "2026-04-01",
            "receipt_upload_id": receipt.id,
        },
    )
    assert response.status_code == 404


def test_create_transaction_with_unowned_category_returns_404(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    other_user = _seed_user(engine, email="categoryowner@example.com")
    assert other_user.id is not None
    other_category = _seed_category(engine, name="Private", user_id=other_user.id)

    response = client.post(
        "/api/v1/transactions",
        json={
            "amount": "10000",
            "currency": "VND",
            "transaction_date": "2026-04-01",
            "category_id": other_category.id,
        },
    )
    assert response.status_code == 404


def test_create_transaction_accepts_system_category(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    system_category = _seed_category(engine, name="Food", is_system=True)

    response = client.post(
        "/api/v1/transactions",
        json={
            "amount": "55000",
            "currency": "VND",
            "transaction_date": "2026-04-01",
            "category_id": system_category.id,
            "merchant_name": "Pho 24",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["category_id"] == system_category.id


def test_create_transaction_remembers_merchant_category_mapping(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    food_category = _seed_category(engine, name="Food", is_system=True)

    first = client.post(
        "/api/v1/transactions",
        json={
            "amount": "70000",
            "currency": "VND",
            "transaction_date": "2026-04-02",
            "category_id": food_category.id,
            "merchant_name": "Pho Hanoi",
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/transactions",
        json={
            "amount": "85000",
            "currency": "VND",
            "transaction_date": "2026-04-03",
            "merchant_name": "Pho Hanoi",
        },
    )
    assert second.status_code == 201
    assert second.json()["category_id"] == food_category.id

    with Session(engine) as session:
        mappings = session.exec(
            select(UserMerchantMapping).where(
                UserMerchantMapping.user_id == auth_user.id,
            ),
        ).all()
        assert len(mappings) == 1
        assert mappings[0].category_id == food_category.id


# -------------------- GET /transactions --------------------


def _create_transaction(
    engine: Engine,
    user_id: int,
    transaction_date: date,
    amount: str = "10000",
    merchant_name: str | None = None,
    category_id: int | None = None,
) -> Transaction:
    with Session(engine) as session:
        record = Transaction(
            user_id=user_id,
            category_id=category_id,
            merchant_name=merchant_name,
            amount=Decimal(amount),
            currency="VND",
            transaction_date=transaction_date,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record


def test_list_transactions_returns_only_current_user_records(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    other = _seed_user(engine, email="leak@example.com")
    assert other.id is not None

    _create_transaction(engine, user_id=auth_user.id, transaction_date=date(2026, 4, 1))
    _create_transaction(engine, user_id=other.id, transaction_date=date(2026, 4, 1))

    response = client.get("/api/v1/transactions")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["user_id"] == auth_user.id


def test_list_transactions_default_sort_desc(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    _create_transaction(engine, user_id=auth_user.id, transaction_date=date(2026, 4, 1))
    _create_transaction(engine, user_id=auth_user.id, transaction_date=date(2026, 4, 5))
    _create_transaction(engine, user_id=auth_user.id, transaction_date=date(2026, 4, 3))

    response = client.get("/api/v1/transactions")
    body = response.json()
    dates = [item["transaction_date"] for item in body["items"]]
    assert dates == ["2026-04-05", "2026-04-03", "2026-04-01"]


def test_list_transactions_filter_by_date_range(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    base_date = date(2026, 4, 1)
    for offset in range(5):
        _create_transaction(
            engine,
            user_id=auth_user.id,
            transaction_date=base_date + timedelta(days=offset),
        )

    response = client.get(
        "/api/v1/transactions",
        params={"start_date": "2026-04-02", "end_date": "2026-04-04"},
    )
    body = response.json()
    assert body["meta"]["total"] == 3
    dates = sorted(item["transaction_date"] for item in body["items"])
    assert dates == ["2026-04-02", "2026-04-03", "2026-04-04"]


def test_list_transactions_filter_by_category(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    food = _seed_category(engine, name="Food", is_system=True)
    travel = _seed_category(engine, name="Travel", is_system=True)
    _create_transaction(
        engine,
        user_id=auth_user.id,
        transaction_date=date(2026, 4, 1),
        category_id=food.id,
    )
    _create_transaction(
        engine,
        user_id=auth_user.id,
        transaction_date=date(2026, 4, 2),
        category_id=travel.id,
    )

    response = client.get(
        "/api/v1/transactions",
        params={"category_id": food.id},
    )
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["items"][0]["category_id"] == food.id


def test_list_transactions_filter_by_merchant_partial(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    _create_transaction(
        engine,
        user_id=auth_user.id,
        transaction_date=date(2026, 4, 1),
        merchant_name="Pho 24",
    )
    _create_transaction(
        engine,
        user_id=auth_user.id,
        transaction_date=date(2026, 4, 2),
        merchant_name="Highlands Coffee",
    )

    response = client.get("/api/v1/transactions", params={"merchant": "pho"})
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["items"][0]["merchant_name"] == "Pho 24"


def test_list_transactions_pagination(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    for day in range(1, 11):
        _create_transaction(
            engine,
            user_id=auth_user.id,
            transaction_date=date(2026, 4, day),
        )

    page_one = client.get("/api/v1/transactions", params={"page": 1, "size": 4}).json()
    page_two = client.get("/api/v1/transactions", params={"page": 2, "size": 4}).json()
    page_three = client.get("/api/v1/transactions", params={"page": 3, "size": 4}).json()

    assert page_one["meta"] == {"total": 10, "page": 1, "size": 4}
    assert len(page_one["items"]) == 4
    assert len(page_two["items"]) == 4
    assert len(page_three["items"]) == 2

    seen_ids = {item["id"] for page in (page_one, page_two, page_three) for item in page["items"]}
    assert len(seen_ids) == 10


def test_list_transactions_invalid_date_range_returns_400(
    client: TestClient,
    auth_user: User,
) -> None:
    response = client.get(
        "/api/v1/transactions",
        params={"start_date": "2026-04-10", "end_date": "2026-04-01"},
    )
    assert response.status_code == 400


def test_list_transactions_size_limit_enforced(
    client: TestClient,
    auth_user: User,
) -> None:
    response = client.get("/api/v1/transactions", params={"size": 500})
    assert response.status_code == 422
