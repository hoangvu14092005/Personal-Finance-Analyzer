from __future__ import annotations

import json
from pathlib import Path

from pfa_shared.enums import ReceiptStatus
from sqlmodel import Session, select

from app.core.database import engine
from app.integrations.ocr import get_ocr_provider
from app.models.entities import OcrResult, ReceiptUpload


# This baseline async-like flow runs in FastAPI BackgroundTasks for MVP local.
def process_receipt_ocr(receipt_id: int) -> None:
    provider = get_ocr_provider()

    with Session(engine) as session:
        receipt = session.get(ReceiptUpload, receipt_id)
        if receipt is None:
            return

        receipt.status = ReceiptStatus.PROCESSING.value
        receipt.error_code = None
        receipt.error_message = None
        session.add(receipt)
        session.commit()

        file_path = Path("data/receipts") / receipt.storage_key
        try:
            raw = provider.extract_text(file_path)
            normalized = provider.normalize_receipt(raw)

            payload = {
                "merchant": normalized.merchant,
                "transaction_date": normalized.transaction_date,
                "total_amount": str(normalized.total_amount),
                "currency": normalized.currency,
            }

            existing = session.exec(
                select(OcrResult).where(OcrResult.receipt_upload_id == receipt_id),
            ).first()
            if existing is None:
                result = OcrResult(
                    receipt_upload_id=receipt_id,
                    provider=raw.provider,
                    raw_text=raw.raw_text,
                    confidence=raw.confidence,
                    normalized_payload=json.dumps(payload),
                    status=ReceiptStatus.READY.value,
                )
                session.add(result)
            else:
                existing.provider = raw.provider
                existing.raw_text = raw.raw_text
                existing.confidence = raw.confidence
                existing.normalized_payload = json.dumps(payload)
                existing.status = ReceiptStatus.READY.value
                session.add(existing)

            receipt.status = ReceiptStatus.READY.value
            receipt.error_code = None
            receipt.error_message = None
            session.add(receipt)
            session.commit()
        except Exception as exc:
            receipt.status = ReceiptStatus.FAILED.value
            receipt.error_code = "ocr_failed"
            receipt.error_message = str(exc)[:500]
            session.add(receipt)
            session.commit()
