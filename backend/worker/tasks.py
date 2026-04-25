"""TaskIQ worker tasks.

M5 refactor:
- Bỏ raw SQL, dùng SQLModel ORM (cùng `pfa_shared.entities` với API).
- Bỏ hardcoded `Path("data/receipts")`, dùng `pfa_shared.storage` adapter
  (local hoặc S3 tùy `STORAGE_BACKEND` env var).
- Tách core logic `run_ocr_for_receipt(session, storage, provider, receipt_id)`
  để test có thể unit-test với SQLite + LocalStorage.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

from pfa_shared.entities import OcrResult, ReceiptUpload
from pfa_shared.enums import ReceiptStatus
from pfa_shared.storage import (
    StorageNotFoundError,
    StorageService,
    build_storage_service,
)
from sqlmodel import Session, create_engine, select

from ocr_provider import OCRProvider, get_ocr_provider
from worker_app import broker, settings


def build_ping_response() -> str:
    return "ping"


@broker.task
async def ping_task() -> str:
    return build_ping_response()


def run_ocr_for_receipt(
    session: Session,
    storage: StorageService,
    provider: OCRProvider,
    receipt_id: int,
) -> str:
    """Core logic của OCR job — testable không cần Redis/TaskIQ.

    Returns one of: "missing_receipt", "ready", "failed".
    """
    receipt = session.get(ReceiptUpload, receipt_id)
    if receipt is None:
        return "missing_receipt"

    # Bước 1: đánh dấu PROCESSING (idempotent — chạy lại task không sao).
    receipt.status = ReceiptStatus.PROCESSING.value
    receipt.error_code = None
    receipt.error_message = None
    session.add(receipt)
    session.commit()

    try:
        # Bước 2: tải bytes từ storage (local FS hoặc S3).
        try:
            content = storage.download_bytes(receipt.storage_key)
        except StorageNotFoundError as exc:
            raise RuntimeError(f"storage_key missing: {receipt.storage_key}") from exc

        # Bước 3: gọi OCR provider.
        raw_result = provider.extract_text(content, source_hint=receipt.storage_key)
        normalized = provider.normalize_receipt(raw_result)

        payload = {
            "merchant": normalized.merchant,
            "transaction_date": normalized.transaction_date,
            "total_amount": str(normalized.total_amount),
            "currency": normalized.currency,
        }

        # Bước 4: upsert OcrResult.
        existing = session.exec(
            select(OcrResult).where(OcrResult.receipt_upload_id == receipt_id),
        ).first()
        now = datetime.now(tz=UTC)

        if existing is None:
            session.add(
                OcrResult(
                    receipt_upload_id=receipt_id,
                    provider=raw_result.provider,
                    raw_text=raw_result.raw_text,
                    confidence=raw_result.confidence,
                    normalized_payload=json.dumps(payload),
                    status=ReceiptStatus.READY.value,
                    created_at=now,
                ),
            )
        else:
            existing.provider = raw_result.provider
            existing.raw_text = raw_result.raw_text
            existing.confidence = raw_result.confidence
            existing.normalized_payload = json.dumps(payload)
            existing.status = ReceiptStatus.READY.value
            session.add(existing)

        # Bước 5: đánh dấu receipt READY.
        receipt.status = ReceiptStatus.READY.value
        receipt.error_code = None
        receipt.error_message = None
        session.add(receipt)
        session.commit()
        return "ready"

    except Exception as exc:
        # Rollback bất kỳ pending change → ghi lại receipt với status FAILED.
        session.rollback()
        receipt = session.get(ReceiptUpload, receipt_id)
        if receipt is not None:
            receipt.status = ReceiptStatus.FAILED.value
            receipt.error_code = "ocr_failed"
            receipt.error_message = str(exc)[:500]
            session.add(receipt)
            session.commit()
        return "failed"


@broker.task
async def process_ocr_job(receipt_id: int) -> str:
    """TaskIQ entry point. Tạo engine + session + storage cho mỗi job (worker
    là long-lived; engine pooled qua sqlmodel). Body delegate sang
    `run_ocr_for_receipt` để dễ unit test."""
    engine = create_engine(settings.database_url)
    storage = build_storage_service(settings)
    provider = get_ocr_provider()

    with Session(engine) as session:
        return run_ocr_for_receipt(session, storage, provider, receipt_id)
