from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pfa_shared.enums import ReceiptStatus
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.integrations.storage import get_storage_service
from app.models.entities import Invoice, InvoiceLineItem, OcrResult, ReceiptLineItem, ReceiptUpload, User
from app.schemas.receipts import (
    DraftReviewResponse,
    InvoiceLineItemResponse,
    InvoiceResponse,
    LineItemResponse,
    OcrResultResponse,
    ReceiptStatusResponse,
    ReceiptUploadResponse,
)
from app.services.draft_review import build_draft_review
from app.services.ocr_queue import enqueue_ocr_job
from app.services.receipt_validation import validate_upload_file

router = APIRouter(prefix="/receipts", tags=["receipts"])


def _ensure_receipt_owner(
    session: Session,
    receipt_id: int,
    user_id: int,
) -> ReceiptUpload:
    receipt = session.get(ReceiptUpload, receipt_id)
    if receipt is None or receipt.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    return receipt


@router.post("/upload", response_model=ReceiptUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_receipt(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReceiptUploadResponse:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    file_content = await file.read()
    settings = get_settings()
    validate_upload_file(file, len(file_content), settings.ocr_max_file_size_mb)

    extension = Path(file.filename or "").suffix.lower()
    generated_name = f"{uuid4().hex}{extension}"
    storage_key = f"{current_user.id}/{generated_name}"

    storage = get_storage_service()
    stored_object = storage.upload_bytes(storage_key, file_content, file.content_type or "")

    # Set PROCESSING TRƯỚC khi enqueue để tránh race condition:
    # nếu set sau enqueue, worker có thể finish (READY) trước khi API kịp ghi
    # PROCESSING -> API sẽ ghi đè READY thành PROCESSING -> frontend mãi thấy
    # processing dù đã xong.
    receipt = ReceiptUpload(
        user_id=current_user.id,
        file_name=file.filename or generated_name,
        content_type=file.content_type or "application/octet-stream",
        file_size_bytes=stored_object.size_bytes,
        storage_key=stored_object.storage_key,
        status=ReceiptStatus.PROCESSING.value,
    )
    session.add(receipt)
    session.commit()
    session.refresh(receipt)

    if receipt.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed",
        )

    enqueued = await enqueue_ocr_job(receipt.id)
    if not enqueued:
        # Rollback: queue down -> trả về UPLOADED + error code để frontend
        # có thể retry hoặc fallback sang manual entry. Không chuyển FAILED
        # vì lỗi nằm ở queue, không phải OCR engine.
        receipt.status = ReceiptStatus.UPLOADED.value
        receipt.error_code = "queue_unavailable"
        receipt.error_message = "OCR queue is not available. You can retry later."
        session.add(receipt)
        session.commit()
        session.refresh(receipt)

    return ReceiptUploadResponse(receipt_id=receipt.id, status=receipt.status)


@router.get("/{receipt_id}", response_model=ReceiptStatusResponse)
def get_receipt_status(
    receipt_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReceiptStatusResponse:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    receipt = _ensure_receipt_owner(session, receipt_id, current_user.id)
    return ReceiptStatusResponse(
        receipt_id=receipt.id or receipt_id,
        file_name=receipt.file_name,
        content_type=receipt.content_type,
        status=receipt.status,
        error_code=receipt.error_code,
        error_message=receipt.error_message,
        created_at=receipt.created_at,
    )


@router.get("/{receipt_id}/ocr-result", response_model=OcrResultResponse)
def get_receipt_ocr_result(
    receipt_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> OcrResultResponse:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    _ensure_receipt_owner(session, receipt_id, current_user.id)
    ocr_result = session.exec(
        select(OcrResult).where(OcrResult.receipt_upload_id == receipt_id),
    ).first()
    if ocr_result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OCR result not ready")

    return OcrResultResponse(
        receipt_id=receipt_id,
        provider=ocr_result.provider,
        status=ocr_result.status,
        raw_text=ocr_result.raw_text,
        confidence=ocr_result.confidence,
        normalized_payload=ocr_result.normalized_payload,
    )


@router.get("/{receipt_id}/draft", response_model=DraftReviewResponse)
def get_receipt_draft(
    receipt_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DraftReviewResponse:
    """Trả về payload review draft cho frontend (Phase 3.2).

    Frontend dùng response này render review form đã pre-fill amount/merchant/
    date/currency từ OCR + suggested category từ user merchant mapping.
    When Invoice exists, prefer its data over OcrResult normalized_payload.
    """
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    receipt = _ensure_receipt_owner(session, receipt_id, current_user.id)
    ocr_result = session.exec(
        select(OcrResult).where(OcrResult.receipt_upload_id == receipt_id),
    ).first()
    if ocr_result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OCR result not ready")

    draft = build_draft_review(
        session=session,
        receipt=receipt,
        ocr_result=ocr_result,
        user_id=current_user.id,
    )

    # Check if Invoice exists and prefer its data
    invoice = session.exec(
        select(Invoice).where(Invoice.receipt_upload_id == receipt_id),
    ).first()

    merchant_name = draft.merchant_name
    amount = draft.amount
    transaction_date = draft.transaction_date
    currency = draft.currency

    if invoice is not None:
        if invoice.seller_name:
            merchant_name = invoice.seller_name
        if invoice.grand_total is not None:
            amount = invoice.grand_total
        if invoice.issue_date is not None:
            transaction_date = invoice.issue_date
        if invoice.currency:
            currency = invoice.currency

    # Load line items
    line_items = session.exec(
        select(ReceiptLineItem)
        .where(ReceiptLineItem.receipt_upload_id == receipt_id)
        .order_by(ReceiptLineItem.line_number),
    ).all()

    return DraftReviewResponse(
        receipt_id=draft.receipt_id,
        receipt_status=draft.receipt_status,
        provider=draft.provider,
        confidence=draft.confidence,
        merchant_name=merchant_name,
        transaction_date=transaction_date,
        amount=amount,
        currency=currency,
        suggested_category_id=draft.suggested_category_id,
        raw_text=draft.raw_text,
        line_items=[
            LineItemResponse(
                id=item.id or 0,
                line_number=item.line_number,
                item_name=item.item_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
                category_id=item.category_id,
            )
            for item in line_items
        ],
    )


@router.get("/{receipt_id}/invoice", response_model=InvoiceResponse)
def get_receipt_invoice(
    receipt_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> InvoiceResponse:
    """Return full invoice data with nested line items."""
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    _ensure_receipt_owner(session, receipt_id, current_user.id)

    invoice = session.exec(
        select(Invoice).where(Invoice.receipt_upload_id == receipt_id),
    ).first()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    line_items = session.exec(
        select(InvoiceLineItem)
        .where(InvoiceLineItem.invoice_id == invoice.id)
        .order_by(InvoiceLineItem.line_number),
    ).all()

    return InvoiceResponse(
        id=invoice.id or 0,
        receipt_upload_id=invoice.receipt_upload_id,
        invoice_number=invoice.invoice_number,
        template_symbol=invoice.template_symbol,
        issue_date=invoice.issue_date,
        tax_lookup_code=invoice.tax_lookup_code,
        currency=invoice.currency,
        seller_name=invoice.seller_name,
        seller_tax_id=invoice.seller_tax_id,
        seller_address=invoice.seller_address,
        buyer_name=invoice.buyer_name,
        buyer_tax_id=invoice.buyer_tax_id,
        buyer_address=invoice.buyer_address,
        payment_method=invoice.payment_method,
        subtotal_before_tax=invoice.subtotal_before_tax,
        total_tax=invoice.total_tax,
        grand_total=invoice.grand_total,
        amount_in_words=invoice.amount_in_words,
        digital_signature=invoice.digital_signature,
        signing_date=invoice.signing_date,
        lookup_link=invoice.lookup_link,
        line_items=[
            InvoiceLineItemResponse(
                id=item.id or 0,
                line_number=item.line_number,
                item_name=item.item_name,
                unit=item.unit,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
                vat_rate=item.vat_rate,
                vat_amount=item.vat_amount,
            )
            for item in line_items
        ],
    )
