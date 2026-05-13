"""TaskIQ worker tasks: ping_task và process_ocr_job.

M5 refactor:
- Dùng SQLModel ORM thay vì raw SQL
- Dùng storage adapter (local/S3) thay vì hardcoded Path
- Tách core logic `run_ocr_for_receipt()` để dễ unit test

OCR Pipeline:
1. Receipt uploaded → status=UPLOADED
2. Worker nhận job → status=PROCESSING
3. Download bytes từ storage → OCR extract → Parse
4. Save OcrResult → status=READY (hoặc FAILED nếu lỗi)
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
    """Helper cho ping_task test."""
    return "ping"


@broker.task
async def ping_task() -> str:
    """Demo task để verify worker hoạt động."""
    return build_ping_response()


def run_ocr_for_receipt(
    session: Session,
    storage: StorageService,
    provider: OCRProvider,
    receipt_id: int,
) -> str:
    """Core OCR logic - testable không cần Redis/TaskIQ.
    
    Flow:
    1. Mark PROCESSING
    2. Download bytes từ storage
    3. OCR extract + normalize
    4. Upsert OcrResult
    5. Mark READY (hoặc FAILED nếu exception)
    
    Returns:
        "missing_receipt" | "ready" | "failed"
    """
    receipt = session.get(ReceiptUpload, receipt_id)
    if receipt is None:
        return "missing_receipt"

    # Step 1: Mark PROCESSING (idempotent)
    receipt.status = ReceiptStatus.PROCESSING.value
    receipt.error_code = None
    receipt.error_message = None
    session.add(receipt)
    session.commit()

    try:
        # Step 2: Download bytes
        try:
            content = storage.download_bytes(receipt.storage_key)
        except StorageNotFoundError as exc:
            raise RuntimeError(f"storage_key missing: {receipt.storage_key}") from exc

        # Step 3: OCR
        raw_result = provider.extract_text(content, source_hint=receipt.storage_key)
        normalized = provider.normalize_receipt(raw_result)

        payload = {
            "merchant": normalized.merchant,
            "transaction_date": normalized.transaction_date,
            "total_amount": str(normalized.total_amount),
            "currency": normalized.currency,
        }

        # Step 4: Upsert OcrResult
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

        # Step 5: Mark READY
        receipt.status = ReceiptStatus.READY.value
        receipt.error_code = None
        receipt.error_message = None
        session.add(receipt)
        session.commit()
        return "ready"

    except Exception as exc:
        # Rollback + mark FAILED
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
    """TaskIQ entry point: tạo engine/session/storage rồi delegate.

    Worker là long-lived process, engine pooled qua SQLModel.
    Sau OCR READY, chain task `index_receipt_text` để embed OCR text cho RAG.
    """
    engine = create_engine(settings.database_url)
    storage = build_storage_service(settings)
    provider = get_ocr_provider()

    with Session(engine) as session:
        result = run_ocr_for_receipt(session, storage, provider, receipt_id)

    # Phase 7 RAG: chain index task nếu OCR thành công.
    # Fail-soft: nếu enqueue fail, log warning, không crash OCR job.
    if result == "ready":
        try:
            from index_tasks import index_receipt_text
            await index_receipt_text.kiq(receipt_id)
        except Exception as exc:
            import logging
            logging.getLogger("worker.ocr").warning(
                "failed to chain index_receipt_text for receipt_id=%d: %s",
                receipt_id, exc,
            )

    return result
