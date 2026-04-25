"""Integration tests cho Receipt upload + status APIs (Phase 2 / M3 stable).

Sau M3:
- `enqueue_ocr_job` được monkeypatch -> không phụ thuộc Redis runtime.
- Test cả 2 path: queue-available (status=processing) và queue-down (status=uploaded + error_code).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from app.models.entities import User
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _cleanup_storage() -> None:
    storage_root = Path("data/receipts")
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
