"""Service `draft_review` (Phase 3.2) — gộp ReceiptUpload + OcrResult + suggested
category thành payload chuẩn cho frontend review form.

Worker `tasks.py` ghi `OcrResult.normalized_payload` dưới dạng JSON string với
schema:
    {
        "merchant": str | None,
        "transaction_date": str | None,   # ISO date
        "total_amount": str | None,        # decimal string
        "currency": str | None,
    }

Service này parse JSON, convert types, và trả về cùng category được suggest từ
mapping merchant của user.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlmodel import Session

from app.core.logging import get_logger
from app.models.entities import OcrResult, ReceiptUpload
from app.services.category_suggestion import suggest_category_for_merchant

logger = get_logger("api.draft_review")


@dataclass(frozen=True)
class DraftReviewData:
    """Dữ liệu draft đã enriched, sẵn sàng để map sang `DraftReviewResponse`."""

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


def _safe_parse_date(value: object) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        logger.warning("draft_review.invalid_date value=%r", value)
        return None


def _safe_parse_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        logger.warning("draft_review.invalid_amount value=%r", value)
        return None


def _safe_parse_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _decode_normalized_payload(raw: str | None) -> dict[str, object]:
    """Parse `OcrResult.normalized_payload` JSON string -> dict.

    Trả dict rỗng khi payload null/blank/invalid JSON để caller dùng default.
    """
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("draft_review.invalid_payload_json raw=%r", raw[:200])
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def build_draft_review(
    session: Session,
    receipt: ReceiptUpload,
    ocr_result: OcrResult,
    user_id: int,
) -> DraftReviewData:
    """Build payload draft review từ receipt + OCR result + suggested category.

    Caller chịu trách nhiệm validate ownership của `receipt` trước khi gọi.
    """
    if receipt.id is None:
        raise ValueError("Receipt id must be set before building draft review")

    payload = _decode_normalized_payload(ocr_result.normalized_payload)
    merchant_name = _safe_parse_str(payload.get("merchant"))
    transaction_date = _safe_parse_date(payload.get("transaction_date"))
    amount = _safe_parse_decimal(payload.get("total_amount"))
    currency = _safe_parse_str(payload.get("currency"))
    if currency is not None:
        currency = currency.upper()

    suggested_category_id = suggest_category_for_merchant(
        session,
        user_id,
        merchant_name,
    )

    return DraftReviewData(
        receipt_id=receipt.id,
        receipt_status=receipt.status,
        provider=ocr_result.provider,
        confidence=ocr_result.confidence,
        merchant_name=merchant_name,
        transaction_date=transaction_date,
        amount=amount,
        currency=currency,
        suggested_category_id=suggested_category_id,
        raw_text=ocr_result.raw_text,
    )
