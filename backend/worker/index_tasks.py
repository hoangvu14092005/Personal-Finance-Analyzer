"""RAG index tasks (Phase 7 — chain sau OCR).

Khi `process_ocr_job` hoàn tất READY → trigger `index_receipt_text` để:
1. Load OCR raw_text.
2. Clean + chunk text.
3. Embed qua sentence-transformers.
4. Save vào `receipt_text_chunks`.

Fail-soft: nếu index fail, receipt vẫn READY, chunks có thể backfill sau.
"""
from __future__ import annotations

from pfa_shared.entities import OcrResult, ReceiptTextChunk, ReceiptUpload
from pfa_shared.logging import get_logger
from sqlmodel import Session, delete, select

from embedding_client import get_embedding_client
from worker_app import broker, engine

logger = get_logger("worker.index")

# Chunking config.
CHUNK_MAX_SIZE = 400  # characters
CHUNK_OVERLAP = 80
SHORT_TEXT_THRESHOLD = 500  # below này không split


def clean_ocr_text(text: str) -> str:
    """Normalize whitespace, strip extra spaces."""
    # Remove multiple whitespace (tabs, newlines, spaces) → single space
    return " ".join(text.split())


def chunk_text(
    text: str,
    max_size: int = CHUNK_MAX_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text thành chunks.

    - Text ≤ SHORT_TEXT_THRESHOLD: return [text] (no split).
    - Text > threshold: split với overlap.
    """
    if len(text) <= SHORT_TEXT_THRESHOLD:
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


def run_index_receipt_text(
    session: Session,
    client: object,  # LocalEmbeddingClient, untyped to avoid circular
    receipt_upload_id: int,
) -> str:
    """Core index logic — testable.

    Returns: "indexed" | "no_ocr" | "no_receipt" | "empty_text".
    Idempotent: xóa chunks cũ trước khi insert mới (re-index nếu chạy lại).
    """
    receipt = session.get(ReceiptUpload, receipt_upload_id)
    if receipt is None:
        return "no_receipt"

    ocr = session.exec(
        select(OcrResult).where(OcrResult.receipt_upload_id == receipt_upload_id),
    ).first()
    if ocr is None or not ocr.raw_text:
        return "no_ocr"

    cleaned = clean_ocr_text(ocr.raw_text)
    if not cleaned.strip():
        return "empty_text"

    # Remove old chunks (idempotent re-index)
    session.exec(
        delete(ReceiptTextChunk).where(  # type: ignore[arg-type]
            ReceiptTextChunk.receipt_upload_id == receipt_upload_id,
        ),
    )

    # Chunk + embed
    chunks = chunk_text(cleaned)
    embeddings = client.embed_batch(chunks)  # type: ignore[attr-defined]

    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
        session.add(
            ReceiptTextChunk(
                user_id=receipt.user_id,
                receipt_upload_id=receipt_upload_id,
                chunk_text=chunk,
                chunk_index=idx,
                embedding=embedding,
                source_type="receipt_ocr",
            ),
        )
    session.commit()

    logger.info(
        "index.receipt_text receipt_id=%d chunks=%d",
        receipt_upload_id, len(chunks),
    )
    return "indexed"


@broker.task
async def index_receipt_text(receipt_upload_id: int) -> str:
    """TaskIQ entry: index receipt OCR text. Dùng engine chung phạm vi process."""
    client = get_embedding_client()

    with Session(engine) as session:
        try:
            return run_index_receipt_text(session, client, receipt_upload_id)
        except Exception as exc:
            logger.exception(
                "index.receipt_text_failed receipt_id=%d error=%s",
                receipt_upload_id, exc,
            )
            return "failed"


__all__ = [
    "CHUNK_MAX_SIZE",
    "CHUNK_OVERLAP",
    "SHORT_TEXT_THRESHOLD",
    "chunk_text",
    "clean_ocr_text",
    "index_receipt_text",
    "run_index_receipt_text",
]
