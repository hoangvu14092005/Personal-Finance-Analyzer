"""Integration tests cho Receipt upload + status APIs (Phase 2 / M3 stable).

Sau M3:
- `enqueue_ocr_job` được monkeypatch -> không phụ thuộc Redis runtime.
- Test cả 2 path: queue-available (status=processing) và queue-down (status=uploaded + error_code).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from app.models.entities import ReceiptUpload, Transaction, User
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session


@pytest.fixture(autouse=True)
def _cleanup_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.integrations.storage.factory import get_storage_service

    monkeypatch.setenv("STORAGE_LOCAL_ROOT", ".tmp/tests/receipts")
    get_settings.cache_clear()
    get_storage_service.cache_clear()

    storage_root = Path(".tmp/tests/receipts")
    if not storage_root.exists():
        return
    for file_path in storage_root.rglob("*"):
        if file_path.is_file():
            file_path.unlink()


def _patch_enqueue(monkeypatch: pytest.MonkeyPatch, *, success: bool) -> list[int]:
    """Monkeypatch `enqueue_ocr_job` ở chỗ receipts.py import nó.

    Trả về list `calls` để test có thể assert đã enqueue receipt id nào.
    """
    calls: list[int] = []

    async def fake_enqueue(receipt_id: int) -> bool:
        calls.append(receipt_id)
        return success

    monkeypatch.setattr("app.api.v1.receipts.enqueue_ocr_job", fake_enqueue)
    return calls


def test_upload_receipt_when_queue_available_sets_processing(
    client: TestClient,
    auth_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_enqueue(monkeypatch, success=True)

    response = client.post(
        "/api/v1/receipts/upload",
        files={"file": ("sample.jpg", b"jpeg-binary", "image/jpeg")},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "processing"
    assert calls == [body["receipt_id"]]


def test_upload_receipt_when_queue_unavailable_rolls_back_to_uploaded(
    client: TestClient,
    auth_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_enqueue(monkeypatch, success=False)

    response = client.post(
        "/api/v1/receipts/upload",
        files={"file": ("sample.jpg", b"jpeg-binary", "image/jpeg")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "uploaded"

    status_response = client.get(f"/api/v1/receipts/{body['receipt_id']}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["status"] == "uploaded"
    assert status_payload["error_code"] == "queue_unavailable"
    assert "retry" in (status_payload["error_message"] or "").lower()


def test_get_receipt_status_for_other_user_returns_404(
    client: TestClient,
    auth_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_enqueue(monkeypatch, success=True)

    upload = client.post(
        "/api/v1/receipts/upload",
        files={"file": ("sample.jpg", b"jpeg-binary", "image/jpeg")},
    )
    receipt_id = upload.json()["receipt_id"]

    # Clear cookie -> next request unauthenticated
    client.cookies.clear()
    unauthorized = client.get(f"/api/v1/receipts/{receipt_id}")
    assert unauthorized.status_code == 401


def test_get_ocr_result_returns_404_before_worker_writes(
    client: TestClient,
    auth_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_enqueue(monkeypatch, success=True)

    upload = client.post(
        "/api/v1/receipts/upload",
        files={"file": ("sample.jpg", b"jpeg-binary", "image/jpeg")},
    )
    receipt_id = upload.json()["receipt_id"]

    ocr = client.get(f"/api/v1/receipts/{receipt_id}/ocr-result")
    # Worker chưa chạy trong test -> chưa có OcrResult row.
    assert ocr.status_code == 404


def test_retry_receipt_resets_status_and_enqueues(
    client: TestClient,
    auth_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_enqueue(monkeypatch, success=True)
    upload = client.post(
        "/api/v1/receipts/upload",
        files={"file": ("sample.jpg", b"jpeg-binary", "image/jpeg")},
    )
    receipt_id = upload.json()["receipt_id"]
    calls = _patch_enqueue(monkeypatch, success=True)

    response = client.post(f"/api/v1/receipts/{receipt_id}/retry")

    assert response.status_code == 200
    assert response.json() == {"receipt_id": receipt_id, "status": "processing"}
    assert calls == [receipt_id]


def test_delete_unlinked_receipt_removes_record(
    client: TestClient,
    auth_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_enqueue(monkeypatch, success=True)
    upload = client.post(
        "/api/v1/receipts/upload",
        files={"file": ("sample.jpg", b"jpeg-binary", "image/jpeg")},
    )
    receipt_id = upload.json()["receipt_id"]

    response = client.delete(f"/api/v1/receipts/{receipt_id}")

    assert response.status_code == 204
    assert response.content == b""
    status_response = client.get(f"/api/v1/receipts/{receipt_id}")
    assert status_response.status_code == 404


def test_delete_linked_receipt_returns_409(
    engine: Engine,
    client: TestClient,
    auth_user: User,
) -> None:
    assert auth_user.id is not None
    with Session(engine) as session:
        receipt = ReceiptUpload(
            user_id=auth_user.id,
            file_name="linked.jpg",
            content_type="image/jpeg",
            file_size_bytes=12,
            storage_key="linked.jpg",
            status="ready",
        )
        session.add(receipt)
        session.flush()
        session.add(
            Transaction(
                user_id=auth_user.id,
                receipt_upload_id=receipt.id,
                amount=Decimal("10000"),
                currency="VND",
                transaction_date=date(2026, 5, 20),
            ),
        )
        session.commit()
        receipt_id = receipt.id

    response = client.delete(f"/api/v1/receipts/{receipt_id}")

    assert response.status_code == 409
