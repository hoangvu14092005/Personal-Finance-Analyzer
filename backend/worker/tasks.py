"""TaskIQ worker tasks: ping_task và process_ocr_job.

M5 refactor:
- Dùng SQLModel ORM thay vì raw SQL
- Dùng storage adapter (local/S3) thay vì hardcoded Path
- Tách core logic `run_ocr_for_receipt()` để dễ unit test

OCR Pipeline:
1. Receipt uploaded → status=UPLOADED
2. Worker nhận job → status=PROCESSING
3. Download bytes từ storage → OCR extract → Parse
4. Save OcrResult + ReceiptLineItems → status=READY (hoặc FAILED nếu lỗi)
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

from pfa_shared.entities import Invoice, InvoiceLineItem, OcrResult, ReceiptLineItem, ReceiptUpload
from pfa_shared.enums import ReceiptStatus
from pfa_shared.storage import (
    StorageNotFoundError,
    StorageService,
    build_storage_service,
)
from sqlmodel import Session, select

from ocr_provider import OCRInvoiceResult, OCRProvider, get_ocr_provider
from worker_app import broker, engine, settings


def build_ping_response() -> str:
    """Helper cho ping_task test."""
    return "ping"


@broker.task
async def ping_task() -> str:
    """Demo task để verify worker hoạt động."""
    return build_ping_response()


def _save_invoice(
    session: Session,
    receipt_id: int,
    user_id: int,
    invoice_result: OCRInvoiceResult,
) -> None:
    """Upsert Invoice + InvoiceLineItems (idempotent).

    Deletes existing Invoice (CASCADE deletes line items) then creates new records.
    line_total auto-calculated as quantity × unit_price when OCR returns None.
    """
    from datetime import date as date_type

    # Delete existing invoice (CASCADE deletes line items)
    existing = session.exec(
        select(Invoice).where(Invoice.receipt_upload_id == receipt_id),
    ).first()
    if existing:
        session.delete(existing)
        session.flush()

    # Create Invoice
    invoice = Invoice(
        receipt_upload_id=receipt_id,
        user_id=user_id,
        invoice_number=invoice_result.invoice_number,
        template_symbol=invoice_result.template_symbol,
        issue_date=date_type.fromisoformat(invoice_result.issue_date) if invoice_result.issue_date else None,
        tax_lookup_code=invoice_result.tax_lookup_code,
        currency=invoice_result.currency,
        seller_name=invoice_result.seller_name,
        seller_tax_id=invoice_result.seller_tax_id,
        seller_address=invoice_result.seller_address,
        buyer_name=invoice_result.buyer_name,
        buyer_tax_id=invoice_result.buyer_tax_id,
        buyer_address=invoice_result.buyer_address,
        payment_method=invoice_result.payment_method,
        subtotal_before_tax=invoice_result.subtotal_before_tax,
        total_tax=invoice_result.total_tax,
        grand_total=invoice_result.grand_total,
        amount_in_words=invoice_result.amount_in_words,
        digital_signature=invoice_result.digital_signature,
        signing_date=date_type.fromisoformat(invoice_result.signing_date) if invoice_result.signing_date else None,
        lookup_link=invoice_result.lookup_link,
    )
    session.add(invoice)
    session.flush()  # Get invoice.id

    # Create InvoiceLineItems
    for idx, item in enumerate(invoice_result.line_items):
        # Auto-calculate line_total when OCR returns None
        line_total = item.line_total if item.line_total is not None else (item.quantity * item.unit_price)
        session.add(InvoiceLineItem(
            invoice_id=invoice.id,
            line_number=idx,
            item_name=item.item_name,
            unit=item.unit,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=line_total,
            vat_rate=item.vat_rate,
            vat_amount=item.vat_amount,
        ))


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
    receipt.ocr_status = "running"
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
            "line_items_count": len(normalized.line_items),
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

        # Step 4.5: Save line items (delete old ones first for idempotency)
        session.exec(
            select(ReceiptLineItem).where(
                ReceiptLineItem.receipt_upload_id == receipt_id,
            ),
        ).all()
        # Delete existing line items
        for old_item in session.exec(
            select(ReceiptLineItem).where(
                ReceiptLineItem.receipt_upload_id == receipt_id,
            ),
        ):
            session.delete(old_item)
        
        # Insert new line items
        for idx, line_item in enumerate(normalized.line_items):
            session.add(
                ReceiptLineItem(
                    user_id=receipt.user_id,
                    receipt_upload_id=receipt_id,
                    line_number=idx,
                    item_name=line_item.item_name,
                    quantity=line_item.quantity,
                    unit_price=line_item.unit_price,
                    total_price=line_item.total_price,
                    created_at=now,
                ),
            )

        # Step 4.6: Invoice extraction + save (new structured data)
        invoice_result = provider.normalize_invoice(raw_result)
        _save_invoice(session, receipt_id, receipt.user_id, invoice_result)

        # Step 4.7: Cache document summary on receipt_uploads for retrieval.
        # Financial source-of-truth is still created later by /receipts/{id}/confirm.
        from datetime import date as date_type

        receipt.merchant_name = normalized.merchant or invoice_result.seller_name
        receipt.total_amount = normalized.total_amount or invoice_result.grand_total
        receipt.currency = normalized.currency or invoice_result.currency
        try:
            receipt.receipt_date = (
                date_type.fromisoformat(normalized.transaction_date)
                if normalized.transaction_date
                else None
            )
        except (TypeError, ValueError):
            receipt.receipt_date = None
        receipt.has_invoice = bool(
            invoice_result.invoice_number
            or invoice_result.seller_tax_id
            or invoice_result.grand_total
            or invoice_result.line_items
        )

        # Step 5: Mark READY
        receipt.status = ReceiptStatus.READY.value
        receipt.ocr_status = "succeeded"
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
            receipt.ocr_status = "failed"
            receipt.error_code = "ocr_failed"
            receipt.error_message = str(exc)[:500]
            session.add(receipt)
            session.commit()
        return "failed"


@broker.task
async def process_ocr_job(receipt_id: int) -> str:
    """TaskIQ entry point: tạo session/storage từ engine dùng chung rồi delegate.

    Engine là singleton phạm vi process (định nghĩa ở `worker_app`), tái sử dụng
    qua các task để tránh rò rỉ connection pool.
    Sau OCR READY, chain task `index_receipt_text` để embed OCR text cho RAG.
    """
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
