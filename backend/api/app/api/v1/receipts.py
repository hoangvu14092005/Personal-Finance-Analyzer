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
from app.models.entities import OcrResult, ReceiptUpload, User
from app.schemas.receipts import OcrResultResponse, ReceiptStatusResponse, ReceiptUploadResponse
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
def upload_receipt(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReceiptUploadResponse:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    file_content = file.file.read()
    settings = get_settings()
    validate_upload_file(file, len(file_content), settings.ocr_max_file_size_mb)

    extension = Path(file.filename or "").suffix.lower()
    generated_name = f"{uuid4().hex}{extension}"
    storage_key = f"{current_user.id}/{generated_name}"

    storage = get_storage_service()
    stored_object = storage.upload_bytes(storage_key, file_content, file.content_type or "")

    receipt = ReceiptUpload(
        user_id=current_user.id,
        file_name=file.filename or generated_name,
        content_type=file.content_type or "application/octet-stream",
        file_size_bytes=stored_object.size_bytes,
        storage_key=stored_object.storage_key,
        status=ReceiptStatus.UPLOADED.value,
    )
    session.add(receipt)
    session.commit()
    session.refresh(receipt)

    if receipt.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed",
        )

    enqueued = enqueue_ocr_job(receipt.id)
    if enqueued:
        receipt.status = ReceiptStatus.PROCESSING.value
    else:
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
