from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ReceiptUploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_id: int
    status: str


class ReceiptStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_id: int
    file_name: str
    content_type: str
    status: str
    error_code: str | None
    error_message: str | None
    created_at: datetime


class OcrResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_id: int
    provider: str
    status: str
    raw_text: str | None
    confidence: float | None
    normalized_payload: str | None


class DraftReviewResponse(BaseModel):
    """Payload gộp cho trang OCR review (Phase 3.2).

    Frontend dùng response này để render form review draft với mọi field
    đã được parse sẵn (amount/currency/date/merchant) và category được suggest
    từ lịch sử user. Confidence kèm theo để UI highlight field nghi ngờ.
    """

    model_config = ConfigDict(extra="forbid")

    receipt_id: int
    receipt_status: str
    provider: str
    confidence: float | None
    merchant_name: str | None
    transaction_date: date | None
    amount: Decimal | None
    currency: str | None
    suggested_category_id: int | None
    raw_text: str | None
