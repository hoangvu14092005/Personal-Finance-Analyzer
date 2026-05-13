"""RAG query functions (Phase 7.5 + 7.6).

- `search_receipt_text`: tìm nội dung chi tiết trong OCR hóa đơn.
- `semantic_search_transactions`: semantic search giao dịch theo ý nghĩa.

Tất cả đều filter user_id server-side trước vector search (isolation).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlmodel import Session, col, select

from app.core.logging import get_logger
from app.models.entities import ReceiptTextChunk, ReceiptUpload, Transaction
from app.services.chat.embedding_client import get_embedding_client
from app.services.date_ranges import RangePreset, resolve_range

logger = get_logger("api.chat.rag")


def _resolve_preset(preset: str) -> RangePreset:
    try:
        return RangePreset(preset)
    except ValueError:
        return RangePreset.THIS_MONTH


def _decimal_str(value: Decimal) -> str:
    return f"{value:.2f}"


def search_receipt_text(
    session: Session,
    user_id: int,
    *,
    query: str,
    date_range: str | None = None,
    merchant: str | None = None,
    receipt_upload_id: int | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Tìm chunks OCR phù hợp với query.

    Strategy:
    1. SQL filter user_id + optional date_range/merchant/receipt_id.
    2. Vector search với cosine distance, top N.
    3. Return chunks kèm metadata.
    """
    capped_limit = min(limit, 10)

    # Embed query
    embedding_client = get_embedding_client()
    query_embedding = embedding_client.embed_sync(query)

    # Base query: join chunks với receipts để lấy metadata
    stmt = select(ReceiptTextChunk, ReceiptUpload).join(
        ReceiptUpload,
        ReceiptTextChunk.receipt_upload_id == ReceiptUpload.id,
    ).where(ReceiptTextChunk.user_id == user_id)

    # Scope filters (SQL first)
    if receipt_upload_id is not None:
        stmt = stmt.where(ReceiptTextChunk.receipt_upload_id == receipt_upload_id)

    # Merchant filter: join với Transaction (nếu có)
    # Receipt có thể chưa có transaction, nhưng nếu user hỏi về merchant,
    # thường là đã có transaction. Dùng EXISTS subquery.
    if merchant:
        escaped = (
            merchant.strip()
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        merchant_tx_ids = select(Transaction.receipt_upload_id).where(
            Transaction.user_id == user_id,
            col(Transaction.merchant_name).ilike(f"%{escaped}%"),
            Transaction.receipt_upload_id.is_not(None),  # type: ignore[union-attr]
        )
        stmt = stmt.where(
            col(ReceiptTextChunk.receipt_upload_id).in_(merchant_tx_ids),
        )

    # Date range filter: filter theo transaction_date của Transaction linked
    if date_range:
        preset = _resolve_preset(date_range)
        range_ = resolve_range(preset)
        date_tx_ids = select(Transaction.receipt_upload_id).where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= range_.start,
            Transaction.transaction_date <= range_.end,
            Transaction.receipt_upload_id.is_not(None),  # type: ignore[union-attr]
        )
        stmt = stmt.where(
            col(ReceiptTextChunk.receipt_upload_id).in_(date_tx_ids),
        )

    # Vector similarity: order by cosine distance ASC (smaller = more similar)
    stmt = stmt.order_by(
        ReceiptTextChunk.embedding.cosine_distance(query_embedding),  # type: ignore[attr-defined]
    ).limit(capped_limit)

    rows = session.exec(stmt).all()

    # Fetch associated transactions for metadata (merchant_name, date, amount)
    receipt_ids = [row[0].receipt_upload_id for row in rows]
    tx_by_receipt: dict[int, Transaction] = {}
    if receipt_ids:
        tx_stmt = select(Transaction).where(
            Transaction.user_id == user_id,
            col(Transaction.receipt_upload_id).in_(receipt_ids),
        )
        for tx in session.exec(tx_stmt).all():
            if tx.receipt_upload_id is not None:
                tx_by_receipt[tx.receipt_upload_id] = tx

    chunks = []
    for row in rows:
        chunk, receipt = row
        tx = tx_by_receipt.get(chunk.receipt_upload_id)
        chunks.append({
            "chunk_text": chunk.chunk_text,
            "receipt_upload_id": chunk.receipt_upload_id,
            "file_name": receipt.file_name,
            "merchant_name": tx.merchant_name if tx else None,
            "transaction_date": (
                tx.transaction_date.isoformat() if tx else None
            ),
            "amount": _decimal_str(tx.amount) if tx else None,
        })

    logger.info(
        "rag.search_receipt user_id=%d query_len=%d results=%d",
        user_id, len(query), len(chunks),
    )

    return {
        "chunks": chunks,
        "query": query,
        "count": len(chunks),
    }


def semantic_search_transactions(
    session: Session,
    user_id: int,
    *,
    query: str,
    date_range: str | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    category_name: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Semantic search transactions theo ý nghĩa.

    Ví dụ: "đồ skincare" match được "Watsons", "Guardian" dù không có keyword.
    """
    capped_limit = min(limit, 20)

    # Embed query
    embedding_client = get_embedding_client()
    query_embedding = embedding_client.embed_sync(query)

    # Base: chỉ transactions đã có embedding
    stmt = select(Transaction).where(
        Transaction.user_id == user_id,
        Transaction.search_embedding.is_not(None),  # type: ignore[union-attr]
    )

    if date_range:
        preset = _resolve_preset(date_range)
        range_ = resolve_range(preset)
        stmt = stmt.where(Transaction.transaction_date >= range_.start)
        stmt = stmt.where(Transaction.transaction_date <= range_.end)

    if amount_min is not None:
        stmt = stmt.where(Transaction.amount >= Decimal(str(amount_min)))
    if amount_max is not None:
        stmt = stmt.where(Transaction.amount <= Decimal(str(amount_max)))

    # Vector similarity
    stmt = stmt.order_by(
        Transaction.search_embedding.cosine_distance(query_embedding),  # type: ignore[attr-defined]
    ).limit(capped_limit)

    rows = session.exec(stmt).all()

    transactions = [
        {
            "id": t.id,
            "merchant_name": t.merchant_name,
            "amount": _decimal_str(t.amount),
            "currency": t.currency,
            "transaction_date": t.transaction_date.isoformat(),
            "note": t.note,
            "category_id": t.category_id,
        }
        for t in rows
    ]

    logger.info(
        "rag.semantic_search_transactions user_id=%d query_len=%d results=%d",
        user_id, len(query), len(transactions),
    )

    return {
        "transactions": transactions,
        "query": query,
        "count": len(transactions),
    }


__all__ = ["search_receipt_text", "semantic_search_transactions"]
