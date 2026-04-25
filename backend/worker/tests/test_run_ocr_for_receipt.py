"""Integration test cho `run_ocr_for_receipt` (M5).

Test core OCR pipeline với SQLite in-memory + LocalStorage tmp dir +
MockOCRProvider. Không cần Redis, MinIO, hay PostgreSQL.

Verify:
- Happy path: receipt UPLOADED -> PROCESSING -> READY + OcrResult được tạo.
- Idempotency: chạy lại task không tạo duplicate OcrResult.
- Missing storage: storage_key không tồn tại -> status FAILED.
- Missing receipt: receipt_id không có trong DB -> trả "missing_receipt".
"""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from pfa_shared.entities import OcrResult, ReceiptUpload, User
from pfa_shared.enums import ReceiptStatus
from pfa_shared.storage.local import LocalStorageService
from sqlmodel import Session, SQLModel, create_engine, select

from ocr_provider import MockOCRProvider
from tasks import run_ocr_for_receipt


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorageService:
    return LocalStorageService(root_dir=tmp_path)


def _seed_user_and_receipt(
    session: Session,
    storage: LocalStorageService,
    storage_key: str = "u1/r1.jpg",
    upload_content: bytes = b"fake-jpeg",
) -> ReceiptUpload:
    """Seed user + receipt + upload bytes vào storage. Trả receipt với id."""
    user = User(email="t@example.com", password_hash="x")
    session.add(user)
    session.commit()
    session.refresh(user)
    assert user.id is not None

    storage.upload_bytes(storage_key, upload_content, "image/jpeg")

    receipt = ReceiptUpload(
        user_id=user.id,
        file_name="r1.jpg",
        content_type="image/jpeg",
        file_size_bytes=len(upload_content),
        storage_key=storage_key,
        status=ReceiptStatus.UPLOADED.value,
    )
    session.add(receipt)
    session.commit()
    session.refresh(receipt)
    return receipt


def test_happy_path_creates_ocr_result_and_marks_ready(
    db_session: Session,
    storage: LocalStorageService,
) -> None:
    receipt = _seed_user_and_receipt(db_session, storage)
    assert receipt.id is not None

    result = run_ocr_for_receipt(db_session, storage, MockOCRProvider(), receipt.id)
    assert result == "ready"

    db_session.refresh(receipt)
    assert receipt.status == ReceiptStatus.READY.value
    assert receipt.error_code is None

    ocr_results = db_session.exec(
        select(OcrResult).where(OcrResult.receipt_upload_id == receipt.id),
    ).all()
    assert len(ocr_results) == 1
    ocr = ocr_results[0]
    assert ocr.status == ReceiptStatus.READY.value
    assert ocr.provider == "mock"
    assert ocr.normalized_payload is not None
    assert "Mock Mart" in ocr.normalized_payload


def test_rerun_is_idempotent_no_duplicate_ocr_results(
    db_session: Session,
    storage: LocalStorageService,
) -> None:
    receipt = _seed_user_and_receipt(db_session, storage)
    assert receipt.id is not None

    # Lần 1: tạo OcrResult mới.
    run_ocr_for_receipt(db_session, storage, MockOCRProvider(), receipt.id)
    # Lần 2: rerun (giả lập task retry) → upsert chứ không INSERT mới.
    run_ocr_for_receipt(db_session, storage, MockOCRProvider(), receipt.id)

    ocr_results = db_session.exec(
        select(OcrResult).where(OcrResult.receipt_upload_id == receipt.id),
    ).all()
    assert len(ocr_results) == 1


def test_storage_missing_marks_receipt_failed(
    db_session: Session,
    storage: LocalStorageService,
) -> None:
    # Seed receipt nhưng KHÔNG upload file vào storage → download_bytes raise.
    user = User(email="t@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    assert user.id is not None

    receipt = ReceiptUpload(
        user_id=user.id,
        file_name="r.jpg",
        content_type="image/jpeg",
        file_size_bytes=1,
        storage_key="u1/missing.jpg",
        status=ReceiptStatus.UPLOADED.value,
    )
    db_session.add(receipt)
    db_session.commit()
    db_session.refresh(receipt)
    assert receipt.id is not None

    result = run_ocr_for_receipt(db_session, storage, MockOCRProvider(), receipt.id)
    assert result == "failed"

    db_session.refresh(receipt)
    assert receipt.status == ReceiptStatus.FAILED.value
    assert receipt.error_code == "ocr_failed"
    assert receipt.error_message is not None
    assert "missing.jpg" in receipt.error_message


def test_missing_receipt_returns_sentinel(
    db_session: Session,
    storage: LocalStorageService,
) -> None:
    result = run_ocr_for_receipt(db_session, storage, MockOCRProvider(), receipt_id=9999)
    assert result == "missing_receipt"
