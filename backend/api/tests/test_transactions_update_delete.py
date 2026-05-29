"""Integration tests cho detail/update/delete transaction APIs."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.models.entities import (
    Category,
    Invoice,
    ReceiptLineItem,
    ReceiptUpload,
    Transaction,
    User,
    UserMerchantMapping,
)
from fastapi.testclient import TestClient
from pfa_shared.enums import ReceiptStatus
from sqlalchemy.engine import Engine
from sqlmodel import Session, select


def _seed_user(engine: Engine, email: str) -> User:
    with Session(engine) as session:
        user = User(
            email=email,
            password_hash="x",
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
    *,
    user_id: int | None = None,
    is_system: bool = False,
) -> Category:
    with Session(engine) as session:
        category = Category(user_id=user_id, name=name, is_system=is_system)
        session.add(category)
        session.commit()
        session.refresh(category)
        return category


def _seed_transaction(
    engine: Engine,
    user_id: int,
    *,
    amount: str = "100000.00",
    merchant_name: str | None = None,
    category_id: int | None = None,
    transaction_date: date = date(2026, 4, 1),
    note: str | None = None,
) -> Transaction:
    with Session(engine) as session:
        record = Transaction(
            user_id=user_id,
            amount=Decimal(amount),
            currency="VND",
            transaction_date=transaction_date,
            merchant_name=merchant_name,
            category_id=category_id,
            note=note,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record


# -------------------- GET /transactions/{id} --------------------


def test_get_transaction_detail_success(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    food = _seed_category(engine, name="Food", is_system=True)
    transaction = _seed_transaction(
        engine,
        user_id=auth_user.id,
        merchant_name="Highlands",
        category_id=food.id,
    )

    response = client.get(f"/api/v1/transactions/{transaction.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == transaction.id
    assert body["merchant_name"] == "Highlands"
    assert body["category_name"] == "Food"


def test_get_transaction_detail_not_owner_returns_404(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    other = _seed_user(engine, email="detail-leak@example.com")
    assert other.id is not None
    transaction = _seed_transaction(engine, user_id=other.id)

    response = client.get(f"/api/v1/transactions/{transaction.id}")

    assert response.status_code == 404


# -------------------- PUT/PATCH /transactions/{id} --------------------


def test_update_transaction_partial_success(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    transaction = _seed_transaction(
        engine,
        user_id=auth_user.id,
        amount="100000",
        note="old note",
    )

    response = client.put(
        f"/api/v1/transactions/{transaction.id}",
        json={"note": "updated", "amount": "150000.00"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["note"] == "updated"
    assert body["amount"] == "150000.00"
    assert body["transaction_date"] == "2026-04-01"


def test_update_transaction_empty_body_returns_current_state(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    transaction = _seed_transaction(
        engine,
        user_id=auth_user.id,
        amount="100000",
        note="keep",
    )

    response = client.put(f"/api/v1/transactions/{transaction.id}", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["amount"] == "100000.00"
    assert body["note"] == "keep"


def test_patch_transaction_partial_success(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    transaction = _seed_transaction(engine, user_id=auth_user.id, note="old")

    response = client.patch(
        f"/api/v1/transactions/{transaction.id}",
        json={"note": "patched"},
    )

    assert response.status_code == 200
    assert response.json()["note"] == "patched"


def test_update_transaction_not_owner_returns_404(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    other = _seed_user(engine, email="other-tx@example.com")
    assert other.id is not None
    transaction = _seed_transaction(engine, user_id=other.id)

    response = client.put(
        f"/api/v1/transactions/{transaction.id}",
        json={"note": "hack"},
    )
    assert response.status_code == 404


def test_update_transaction_unauthenticated_returns_401(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    transaction = _seed_transaction(engine, user_id=auth_user.id)
    client.cookies.clear()

    response = client.put(
        f"/api/v1/transactions/{transaction.id}",
        json={"note": "x"},
    )
    assert response.status_code == 401


def test_update_transaction_with_unowned_category_returns_404(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    transaction = _seed_transaction(engine, user_id=auth_user.id)
    other = _seed_user(engine, email="cat-owner@example.com")
    assert other.id is not None
    private_category = _seed_category(engine, name="Private", user_id=other.id)

    response = client.put(
        f"/api/v1/transactions/{transaction.id}",
        json={"category_id": private_category.id},
    )
    assert response.status_code == 404


def test_update_transaction_with_system_category_succeeds(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    transaction = _seed_transaction(engine, user_id=auth_user.id)
    food = _seed_category(engine, name="Food", is_system=True)

    response = client.put(
        f"/api/v1/transactions/{transaction.id}",
        json={"category_id": food.id},
    )
    assert response.status_code == 200
    assert response.json()["category_id"] == food.id


def test_update_transaction_persists_merchant_mapping_when_both_set(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    food = _seed_category(engine, name="Food", is_system=True)
    transaction = _seed_transaction(
        engine,
        user_id=auth_user.id,
        merchant_name="Highlands",
    )

    response = client.put(
        f"/api/v1/transactions/{transaction.id}",
        json={"category_id": food.id},
    )
    assert response.status_code == 200

    with Session(engine) as session:
        mappings = session.exec(
            select(UserMerchantMapping).where(
                UserMerchantMapping.user_id == auth_user.id,
            ),
        ).all()
        assert len(mappings) == 1
        assert mappings[0].category_id == food.id


def test_update_transaction_rejects_zero_amount(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    transaction = _seed_transaction(engine, user_id=auth_user.id)

    response = client.put(
        f"/api/v1/transactions/{transaction.id}",
        json={"amount": "0"},
    )
    assert response.status_code == 422


def test_update_transaction_rejects_extra_field(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    transaction = _seed_transaction(engine, user_id=auth_user.id)

    response = client.put(
        f"/api/v1/transactions/{transaction.id}",
        json={"unknown_field": "x"},
    )
    assert response.status_code == 422


# -------------------- DELETE /transactions/{id} --------------------


def test_delete_transaction_success_returns_204(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    transaction = _seed_transaction(engine, user_id=auth_user.id)

    response = client.delete(f"/api/v1/transactions/{transaction.id}")
    assert response.status_code == 204
    assert response.content == b""

    with Session(engine) as session:
        assert session.get(Transaction, transaction.id) is None


def test_delete_transaction_unlinks_receipt_evidence(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    with Session(engine) as session:
        receipt = ReceiptUpload(
            user_id=auth_user.id,
            file_name="receipt.jpg",
            content_type="image/jpeg",
            file_size_bytes=12,
            storage_key=f"{auth_user.id}/receipt.jpg",
            status=ReceiptStatus.READY.value,
        )
        session.add(receipt)
        session.flush()

        transaction = Transaction(
            user_id=auth_user.id,
            receipt_upload_id=receipt.id,
            amount=Decimal("100000.00"),
            currency="VND",
            transaction_date=date(2026, 4, 1),
        )
        session.add(transaction)
        session.flush()

        invoice = Invoice(
            user_id=auth_user.id,
            receipt_upload_id=receipt.id,
            transaction_id=transaction.id,
        )
        line_item = ReceiptLineItem(
            user_id=auth_user.id,
            receipt_upload_id=receipt.id,
            transaction_id=transaction.id,
            line_number=0,
            item_name="Coffee",
            quantity=Decimal("1"),
            unit_price=Decimal("100000.00"),
            total_price=Decimal("100000.00"),
        )
        session.add(invoice)
        session.add(line_item)
        session.commit()
        transaction_id = transaction.id
        invoice_id = invoice.id
        line_item_id = line_item.id

    response = client.delete(f"/api/v1/transactions/{transaction_id}")
    assert response.status_code == 204

    with Session(engine) as session:
        assert session.get(Transaction, transaction_id) is None
        invoice = session.get(Invoice, invoice_id)
        line_item = session.get(ReceiptLineItem, line_item_id)
        assert invoice is not None
        assert invoice.transaction_id is None
        assert line_item is not None
        assert line_item.transaction_id is None


def test_delete_transaction_twice_returns_404_second_time(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    transaction = _seed_transaction(engine, user_id=auth_user.id)

    first = client.delete(f"/api/v1/transactions/{transaction.id}")
    assert first.status_code == 204

    second = client.delete(f"/api/v1/transactions/{transaction.id}")
    assert second.status_code == 404


def test_delete_transaction_not_owner_returns_404(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    other = _seed_user(engine, email="del-leak@example.com")
    assert other.id is not None
    transaction = _seed_transaction(engine, user_id=other.id)

    response = client.delete(f"/api/v1/transactions/{transaction.id}")
    assert response.status_code == 404

    # Verify row still exists in DB
    with Session(engine) as session:
        assert session.get(Transaction, transaction.id) is not None


def test_delete_transaction_unauthenticated_returns_401(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    transaction = _seed_transaction(engine, user_id=auth_user.id)
    client.cookies.clear()

    response = client.delete(f"/api/v1/transactions/{transaction.id}")
    assert response.status_code == 401
