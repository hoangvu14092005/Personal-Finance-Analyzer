from __future__ import annotations

from datetime import datetime

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
