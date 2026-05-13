"""Backfill receipt_text_chunks cho receipts đã có OCR (Phase 7).

Chạy 1 lần sau migration để index toàn bộ OCR text chưa có chunks.

Usage:
    python -m scripts.backfill_receipt_embeddings
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running from backend/api folder
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine  # noqa: E402
from app.models.entities import OcrResult, ReceiptTextChunk, ReceiptUpload  # noqa: E402
from app.services.chat.embedding_client import get_embedding_client  # noqa: E402
from sqlmodel import Session, col, select  # noqa: E402

# Import from worker project
worker_path = Path(__file__).parent.parent.parent / "worker"
sys.path.insert(0, str(worker_path))


def clean_ocr_text(text: str) -> str:
    return " ".join(text.split())


def chunk_text(text: str, max_size: int = 400, overlap: int = 80) -> list[str]:
    if len(text) <= 500:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_size, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def backfill() -> None:
    """Index tất cả receipts có OCR nhưng chưa có chunks."""
    client = get_embedding_client()

    with Session(engine) as session:
        # Find receipts with OcrResult but no chunks
        indexed_ids_stmt = select(ReceiptTextChunk.receipt_upload_id).distinct()
        indexed_ids = {row for row in session.exec(indexed_ids_stmt).all()}

        ocr_stmt = select(OcrResult, ReceiptUpload).join(
            ReceiptUpload,
            OcrResult.receipt_upload_id == ReceiptUpload.id,
        ).where(col(OcrResult.raw_text).is_not(None))

        pending: list[tuple[OcrResult, ReceiptUpload]] = []
        for ocr, receipt in session.exec(ocr_stmt).all():
            if ocr.receipt_upload_id not in indexed_ids and ocr.raw_text:
                pending.append((ocr, receipt))

        print(f"Found {len(pending)} receipts with OCR but no chunks")

        if not pending:
            return

        for ocr, receipt in pending:
            cleaned = clean_ocr_text(ocr.raw_text or "")
            if not cleaned.strip():
                continue

            chunks = chunk_text(cleaned)
            embeddings = client.embed_batch(chunks)  # type: ignore[attr-defined]

            for idx, (chunk, emb) in enumerate(zip(chunks, embeddings, strict=True)):
                session.add(
                    ReceiptTextChunk(
                        user_id=receipt.user_id,
                        receipt_upload_id=ocr.receipt_upload_id,
                        chunk_text=chunk,
                        chunk_index=idx,
                        embedding=emb,
                        source_type="receipt_ocr",
                    ),
                )
            session.commit()
            print(f"  Indexed receipt_id={ocr.receipt_upload_id} chunks={len(chunks)}")

        print("Done.")


if __name__ == "__main__":
    backfill()
