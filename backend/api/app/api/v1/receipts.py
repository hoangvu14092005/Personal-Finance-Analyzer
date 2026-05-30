from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from pfa_shared.enums import ReceiptStatus
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.integrations.storage import get_storage_service
from app.models.entities import (
    OcrResult,
    ReceiptUpload,
    User,
)
from app.schemas.receipts import (
    DraftReviewResponse,
    InvoiceResponse,
    LineItemResponse,
    OcrResultResponse,
    ReceiptConfirmRequest,
    ReceiptConfirmResponse,
    ReceiptImageResponse,
    ReceiptListResponse,
    ReceiptStatusResponse,
    ReceiptUploadResponse,
)
from app.schemas.transactions import TransactionResponse
from app.services.audit import record_audit_event
from app.services.ocr_queue import enqueue_ocr_job
from app.services.receipt_validation import validate_upload_file
from app.services.receipt_workflow import (
    ReceiptListFilters,
    build_receipt_draft_response,
    confirm_receipt_as_transaction,
    delete_receipt_for_user,
    ensure_receipt_owner,
    invoice_response_for_receipt,
    list_receipts_for_user,
    receipt_image_response,
    receipt_line_items_response,
    receipt_transaction_response,
    reset_receipt_for_retry,
    update_receipt_draft_metadata,
)

router = APIRouter(prefix="/receipts", tags=["receipts"])

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _persist_uploaded_receipt(session: Session, receipt: ReceiptUpload) -> ReceiptUpload:
    """Sync DB write cho receipt upload. Chạy off event loop qua run_in_threadpool."""
    session.add(receipt)
    session.commit()
    session.refresh(receipt)
    return receipt


def _mark_queue_unavailable(session: Session, receipt: ReceiptUpload) -> ReceiptUpload:
    """Rollback fail-soft khi queue down (sync DB write)."""
    receipt.status = ReceiptStatus.UPLOADED.value
    receipt.error_code = "queue_unavailable"
    receipt.error_message = "OCR queue is not available. You can retry later."
    session.add(receipt)
    session.commit()
    session.refresh(receipt)
    return receipt


@router.post("", response_model=ReceiptUploadResponse, status_code=status.HTTP_201_CREATED)
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

    # Storage upload là I/O blocking (filesystem/S3) -> chạy off event loop.
    storage = get_storage_service()
    stored_object = await run_in_threadpool(
        storage.upload_bytes, storage_key, file_content, file.content_type or "",
    )

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
        ocr_status="pending",
    )
    # DB write blocking -> off event loop.
    receipt = await run_in_threadpool(_persist_uploaded_receipt, session, receipt)

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
        receipt = await run_in_threadpool(_mark_queue_unavailable, session, receipt)

    await run_in_threadpool(
        record_audit_event,
        session,
        user_id=current_user.id,
        event="receipt.uploaded",
        target_type="receipt",
        target_id=receipt.id,
        metadata={"status": receipt.status},
        commit=True,
    )
    return ReceiptUploadResponse(receipt_id=receipt.id, status=receipt.status)


@router.get("", response_model=ReceiptListResponse)
def list_receipts(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    receipt_date: date | None = Query(default=None),
    created_date: date | None = Query(default=None),
    merchant: str | None = Query(default=None, max_length=255),
    status_filter: str | None = Query(default=None, alias="status", max_length=50),
    ocr_status: str | None = Query(default=None, max_length=50),
    has_transaction: bool | None = Query(default=None),
    has_invoice: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> ReceiptListResponse:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    return list_receipts_for_user(
        session,
        user_id=current_user.id,
        filters=ReceiptListFilters(
            receipt_date=receipt_date,
            created_date=created_date,
            merchant=merchant,
            status_filter=status_filter,
            ocr_status=ocr_status,
            has_transaction=has_transaction,
            has_invoice=has_invoice,
            page=page,
            size=size,
        ),
    )


@router.get("/{receipt_id}", response_model=ReceiptStatusResponse)
def get_receipt_status(
    receipt_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReceiptStatusResponse:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    receipt = ensure_receipt_owner(session, receipt_id, current_user.id)
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

    ensure_receipt_owner(session, receipt_id, current_user.id)
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

    return build_receipt_draft_response(session, receipt_id=receipt_id, user_id=current_user.id)


@router.patch("/{receipt_id}/draft", response_model=DraftReviewResponse)
def update_receipt_draft(
    receipt_id: int,
    payload: ReceiptConfirmRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DraftReviewResponse:
    """Persist lightweight review edits before confirm.

    For now the persisted draft lives as receipt summary metadata. Line-item
    edits can be added later without changing the confirm contract.
    """
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    draft = update_receipt_draft_metadata(
        session,
        receipt_id=receipt_id,
        user_id=current_user.id,
        payload=payload,
    )
    record_audit_event(
        session,
        user_id=current_user.id,
        event="receipt.draft_updated",
        target_type="receipt",
        target_id=receipt_id,
        commit=True,
    )
    return draft


@router.post("/{receipt_id}/retry", response_model=ReceiptUploadResponse)
async def retry_receipt_ocr(
    receipt_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReceiptUploadResponse:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    receipt = await run_in_threadpool(
        reset_receipt_for_retry, session, receipt_id=receipt_id, user_id=current_user.id,
    )
    if receipt.id is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Missing id")
    enqueued = await enqueue_ocr_job(receipt.id)
    if not enqueued:
        receipt = await run_in_threadpool(_mark_queue_unavailable, session, receipt)
    await run_in_threadpool(
        record_audit_event,
        session,
        user_id=current_user.id,
        event="receipt.retry_requested",
        target_type="receipt",
        target_id=receipt.id,
        metadata={"enqueued": enqueued, "status": receipt.status},
        commit=True,
    )
    return ReceiptUploadResponse(receipt_id=receipt.id, status=receipt.status)


@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receipt(
    receipt_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    receipt = delete_receipt_for_user(session, receipt_id=receipt_id, user_id=current_user.id)
    try:
        get_storage_service().delete(receipt.storage_key)
    except Exception:  # noqa: BLE001 - DB delete already succeeded; storage cleanup can be retried later.
        pass
    record_audit_event(
        session,
        user_id=current_user.id,
        event="receipt.deleted",
        target_type="receipt",
        target_id=receipt_id,
        commit=True,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{receipt_id}/confirm", response_model=ReceiptConfirmResponse)
def confirm_receipt(
    receipt_id: int,
    payload: ReceiptConfirmRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReceiptConfirmResponse:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    response = confirm_receipt_as_transaction(
        session,
        receipt_id=receipt_id,
        user_id=current_user.id,
        payload=payload,
        skip_embedding=os.getenv("PFA_SKIP_EMBEDDING") == "1",
    )
    record_audit_event(
        session,
        user_id=current_user.id,
        event="receipt.confirmed",
        target_type="receipt",
        target_id=receipt_id,
        metadata={"transaction_id": response.transaction_id},
        commit=True,
    )
    return response


@router.get("/{receipt_id}/image", response_model=ReceiptImageResponse)
def get_receipt_image(
    receipt_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReceiptImageResponse:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return receipt_image_response(session, receipt_id=receipt_id, user_id=current_user.id)


@router.get("/{receipt_id}/line-items", response_model=list[LineItemResponse])
def get_receipt_line_items(
    receipt_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[LineItemResponse]:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return receipt_line_items_response(session, receipt_id=receipt_id, user_id=current_user.id)


@router.get("/{receipt_id}/transaction", response_model=TransactionResponse)
def get_receipt_transaction(
    receipt_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return receipt_transaction_response(session, receipt_id=receipt_id, user_id=current_user.id)


@router.get("/{receipt_id}/invoice", response_model=InvoiceResponse)
def get_receipt_invoice(
    receipt_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> InvoiceResponse:
    """Return full invoice data with nested line items."""
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return invoice_response_for_receipt(session, receipt_id=receipt_id, user_id=current_user.id)
