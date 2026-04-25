"""Integration tests cho `GET /receipts/{id}/draft` (Phase 3.2)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.models.entities import (
    Category,
    OcrResult,
    ReceiptUpload,
    User,
    UserMerchantMapping,
)
from fastapi.testclient import TestClient
from pfa_shared.enums import ReceiptStatus
from sqlalchemy.engine import Engine
from sqlmodel import Session


@pytest.fixture(autouse=True)
def _cleanup_storage() -> None:
    storage_root = Path("data/receipts")
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
