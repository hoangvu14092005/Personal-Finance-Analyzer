"""Integration tests cho `GET /receipts/{id}/draft` (Phase 3.2)."""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from app.models.entities import (
    Category,
    OcrResult,
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


@pytest.fixture(autouse=True)
def _cleanup_storage() -> None:
    storage_root = Path(".tmp/tests/receipts")
    if not storage_root.exists():
        return
    for file_path in storage_root.rglob("*"):
        if file_path.is_file():
            file_path.unlink()


def _seed_receipt_with_ocr(
    engine: Engine,
    user_id: int,
    *,
    payload: dict[str, object] | None = None,
    confidence: float | None = 0.92,
    receipt_status: str = ReceiptStatus.READY.value,
    raw_text: str | None = "RAW",
) -> int:
    """Seed receipt + ocr_result. Trả về receipt_id (primitive) để tránh
    DetachedInstanceError khi access attribute ngoài session."""
    with Session(engine) as session:
        receipt = ReceiptUpload(
            user_id=user_id,
            file_name="r.jpg",
            content_type="image/jpeg",
            file_size_bytes=1,
            storage_key=f"{user_id}/r.jpg",
            status=receipt_status,
        )
        session.add(receipt)
        session.commit()
        session.refresh(receipt)
        receipt_id = receipt.id
        assert receipt_id is not None

        ocr = OcrResult(
            receipt_upload_id=receipt_id,
            provider="mock",
            raw_text=raw_text,
            confidence=confidence,
            normalized_payload=json.dumps(payload) if payload is not None else None,
            status=ReceiptStatus.READY.value,
        )
        session.add(ocr)
        session.commit()

        return receipt_id


def test_get_draft_returns_parsed_payload(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    receipt_id = _seed_receipt_with_ocr(
        engine,
        user_id=auth_user.id,
        payload={
            "merchant": "  Pho 24  ",
            "transaction_date": "2026-04-15",
            "total_amount": "125000.00",
            "currency": "vnd",
        },
        confidence=0.81,
    )

    response = client.get(f"/api/v1/receipts/{receipt_id}/draft")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["receipt_id"] == receipt_id
    assert body["receipt_status"] == "ready"
    assert body["provider"] == "mock"
    assert body["confidence"] == 0.81
    assert body["merchant_name"] == "Pho 24"
    assert body["transaction_date"] == "2026-04-15"
    assert body["amount"] == "125000.00"
    assert body["currency"] == "VND"
    assert body["suggested_category_id"] is None
    assert body["raw_text"] == "RAW"


def test_get_draft_includes_suggested_category_from_user_mapping(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    with Session(engine) as session:
        food = Category(name="Food", is_system=True)
        session.add(food)
        session.commit()
        session.refresh(food)
        food_id = food.id
        assert food_id is not None

        mapping = UserMerchantMapping(
            user_id=auth_user.id,
            raw_merchant_name="Pho 24",
            normalized_merchant_name="pho 24",
            category_id=food_id,
        )
        session.add(mapping)
        session.commit()

    receipt_id = _seed_receipt_with_ocr(
        engine,
        user_id=auth_user.id,
        payload={
            "merchant": "Pho 24",
            "transaction_date": "2026-04-15",
            "total_amount": "55000",
            "currency": "VND",
        },
    )

    response = client.get(f"/api/v1/receipts/{receipt_id}/draft")
    assert response.status_code == 200
    body = response.json()
    assert body["suggested_category_id"] == food_id


def test_get_draft_handles_invalid_payload_gracefully(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    receipt_id = _seed_receipt_with_ocr(
        engine,
        user_id=auth_user.id,
        payload={
            "merchant": None,
            "transaction_date": "not-a-date",
            "total_amount": "not-a-number",
            "currency": None,
        },
    )

    response = client.get(f"/api/v1/receipts/{receipt_id}/draft")
    assert response.status_code == 200
    body = response.json()
    assert body["merchant_name"] is None
    assert body["transaction_date"] is None
    assert body["amount"] is None
    assert body["currency"] is None


def test_get_draft_returns_404_when_no_ocr_result(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    with Session(engine) as session:
        receipt = ReceiptUpload(
            user_id=auth_user.id,
            file_name="r.jpg",
            content_type="image/jpeg",
            file_size_bytes=1,
            storage_key=f"{auth_user.id}/r.jpg",
            status=ReceiptStatus.PROCESSING.value,
        )
        session.add(receipt)
        session.commit()
        session.refresh(receipt)
        receipt_id = receipt.id
        assert receipt_id is not None

    response = client.get(f"/api/v1/receipts/{receipt_id}/draft")
    assert response.status_code == 404


def test_get_draft_for_other_user_returns_404(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    with Session(engine) as session:
        other = User(
            email="leak-draft@example.com",
            password_hash="x",
            currency="VND",
            timezone="Asia/Ho_Chi_Minh",
            locale="vi-VN",
        )
        session.add(other)
        session.commit()
        session.refresh(other)
        other_id = other.id
        assert other_id is not None
    receipt_id = _seed_receipt_with_ocr(
        engine,
        user_id=other_id,
        payload={"merchant": "X"},
    )

    response = client.get(f"/api/v1/receipts/{receipt_id}/draft")
    assert response.status_code == 404


def test_get_draft_unauthenticated_returns_401(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    receipt_id = _seed_receipt_with_ocr(
        engine,
        user_id=auth_user.id,
        payload={"merchant": "X"},
    )

    client.cookies.clear()
    response = client.get(f"/api/v1/receipts/{receipt_id}/draft")
    assert response.status_code == 401


def test_confirm_receipt_creates_transaction_once_and_keeps_receipt(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    receipt_id = _seed_receipt_with_ocr(
        engine,
        user_id=auth_user.id,
        payload={
            "merchant": "Highlands Coffee",
            "transaction_date": "2026-05-18",
            "total_amount": "68000.00",
            "currency": "VND",
        },
    )

    response = client.post(f"/api/v1/receipts/{receipt_id}/confirm", json={})
    assert response.status_code == 200, response.text
    body = response.json()
    tx_id = body["transaction_id"]
    assert body["receipt_id"] == receipt_id

    with Session(engine) as session:
        tx_rows = session.exec(
            select(Transaction).where(Transaction.receipt_upload_id == receipt_id),
        ).all()
        assert len(tx_rows) == 1
        tx = tx_rows[0]
        assert tx.id == tx_id
        assert tx.user_id == auth_user.id
        assert tx.merchant_name == "Highlands Coffee"
        assert tx.amount == Decimal("68000.00")
        assert tx.transaction_date.isoformat() == "2026-05-18"
        assert tx.source == "ocr"
        assert tx.status == "confirmed"
        assert tx.confirmed_at is not None

    second = client.post(
        f"/api/v1/receipts/{receipt_id}/confirm",
        json={"amount": "70000.00", "note": "corrected total"},
    )
    assert second.status_code == 200, second.text
    assert second.json()["transaction_id"] == tx_id

    with Session(engine) as session:
        tx_rows = session.exec(
            select(Transaction).where(Transaction.receipt_upload_id == receipt_id),
        ).all()
        assert len(tx_rows) == 1
        assert tx_rows[0].amount == Decimal("70000.00")
        assert tx_rows[0].note == "corrected total"

    linked = client.get(f"/api/v1/receipts/{receipt_id}/transaction")
    assert linked.status_code == 200
    assert linked.json()["id"] == tx_id

    back_link = client.get(f"/api/v1/transactions/{tx_id}/receipt")
    assert back_link.status_code == 200
    assert back_link.json()["receipt_id"] == receipt_id
    assert back_link.json()["linked_transaction"]["transaction_id"] == tx_id


def test_receipt_retrieval_filters_document_dates_and_line_items(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    receipt_id = _seed_receipt_with_ocr(
        engine,
        user_id=auth_user.id,
        payload={
            "merchant": "Coopmart",
            "transaction_date": "2026-05-28",
            "total_amount": "852000.00",
            "currency": "VND",
        },
    )
    with Session(engine) as session:
        receipt = session.get(ReceiptUpload, receipt_id)
        assert receipt is not None
        receipt.merchant_name = "Coopmart"
        receipt.receipt_date = date(2026, 5, 28)
        receipt.total_amount = Decimal("852000.00")
        receipt.currency = "VND"
        session.add(
            ReceiptLineItem(
                user_id=auth_user.id,
                receipt_upload_id=receipt_id,
                line_number=0,
                item_name="Gạo lài thơm",
                quantity=Decimal("1"),
                unit_price=Decimal("145000.00"),
                total_price=Decimal("145000.00"),
            ),
        )
        session.add(receipt)
        session.commit()

    receipt_list = client.get("/api/v1/receipts", params={"receipt_date": "2026-05-28"})
    assert receipt_list.status_code == 200
    payload = receipt_list.json()
    assert payload["meta"]["total"] == 1
    assert payload["items"][0]["receipt_id"] == receipt_id
    assert payload["items"][0]["merchant_name"] == "Coopmart"
    assert payload["items"][0]["linked_transaction"] is None

    line_items = client.get(f"/api/v1/receipts/{receipt_id}/line-items")
    assert line_items.status_code == 200
    assert line_items.json()[0]["item_name"] == "Gạo lài thơm"
