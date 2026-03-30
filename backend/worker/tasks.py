from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pfa_shared.enums import ReceiptStatus
from sqlalchemy import create_engine, text

from ocr_provider import get_ocr_provider
from worker_app import broker, settings


def build_ping_response() -> str:
    return "ping"


@broker.task
async def ping_task() -> str:
    return build_ping_response()


@broker.task
async def process_ocr_job(receipt_id: int) -> str:
    engine = create_engine(settings.database_url)
    provider = get_ocr_provider()

    with engine.begin() as connection:
        receipt_row = connection.execute(
            text(
                """
                SELECT id, storage_key
                FROM receipt_uploads
                WHERE id = :receipt_id
                """,
            ),
            {"receipt_id": receipt_id},
        ).mappings().first()

        if receipt_row is None:
            return "missing_receipt"

        connection.execute(
            text(
                """
                UPDATE receipt_uploads
                SET status = :status, error_code = NULL, error_message = NULL
                WHERE id = :receipt_id
                """,
            ),
            {
                "status": ReceiptStatus.PROCESSING.value,
                "receipt_id": receipt_id,
            },
        )

        storage_path = Path("data/receipts") / str(receipt_row["storage_key"])
        try:
            raw_result = provider.extract_text(storage_path)
            normalized = provider.normalize_receipt(raw_result)

            payload = {
                "merchant": normalized.merchant,
                "transaction_date": normalized.transaction_date,
                "total_amount": str(normalized.total_amount),
                "currency": normalized.currency,
            }
            now = datetime.now(tz=UTC)

            existing = connection.execute(
                text(
                    "SELECT id FROM ocr_results WHERE receipt_upload_id = :receipt_id",
                ),
                {"receipt_id": receipt_id},
            ).first()

            if existing is None:
                connection.execute(
                    text(
                        """
                        INSERT INTO ocr_results (
                            receipt_upload_id,
                            provider,
                            raw_text,
                            confidence,
                            normalized_payload,
                            status,
                            created_at
                        ) VALUES (
                            :receipt_id,
                            :provider,
                            :raw_text,
                            :confidence,
                            :normalized_payload,
                            :status,
                            :created_at
                        )
                        """,
                    ),
                    {
                        "receipt_id": receipt_id,
                        "provider": raw_result.provider,
                        "raw_text": raw_result.raw_text,
                        "confidence": raw_result.confidence,
                        "normalized_payload": json.dumps(payload),
                        "status": ReceiptStatus.READY.value,
                        "created_at": now,
                    },
                )
            else:
                connection.execute(
                    text(
                        """
                        UPDATE ocr_results
                        SET provider = :provider,
                            raw_text = :raw_text,
                            confidence = :confidence,
                            normalized_payload = :normalized_payload,
                            status = :status
                        WHERE receipt_upload_id = :receipt_id
                        """,
                    ),
                    {
                        "receipt_id": receipt_id,
                        "provider": raw_result.provider,
                        "raw_text": raw_result.raw_text,
                        "confidence": raw_result.confidence,
                        "normalized_payload": json.dumps(payload),
                        "status": ReceiptStatus.READY.value,
                    },
                )

            connection.execute(
                text(
                    """
                    UPDATE receipt_uploads
                    SET status = :status,
                        error_code = NULL,
                        error_message = NULL
                    WHERE id = :receipt_id
                    """,
                ),
                {
                    "status": ReceiptStatus.READY.value,
                    "receipt_id": receipt_id,
                },
            )

            return "ready"
        except Exception as exc:
            connection.execute(
                text(
                    """
                    UPDATE receipt_uploads
                    SET status = :status,
                        error_code = :error_code,
                        error_message = :error_message
                    WHERE id = :receipt_id
                    """,
                ),
                {
                    "status": ReceiptStatus.FAILED.value,
                    "error_code": "ocr_failed",
                    "error_message": str(exc)[:500],
                    "receipt_id": receipt_id,
                },
            )
            return "failed"
