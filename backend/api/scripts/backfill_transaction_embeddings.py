"""Backfill search_embedding cho transactions đã tồn tại (Phase 7).

Chạy 1 lần sau migration để embed toàn bộ transactions chưa có embedding.

Usage:
    python -m scripts.backfill_transaction_embeddings
"""
from __future__ import annotations

from app.core.database import engine
from app.models.entities import Transaction
from app.services.chat.embedding_client import get_embedding_client
from sqlmodel import Session, col, select

BATCH_SIZE = 50


def _build_search_text(merchant_name: str | None, note: str | None) -> str:
    parts = [p.strip() for p in (merchant_name, note) if p and p.strip()]
    return " ".join(parts)


def backfill() -> None:
    """Embed tất cả transactions có search_embedding=NULL."""
    client = get_embedding_client()

    with Session(engine) as session:
        stmt = select(Transaction).where(col(Transaction.search_embedding).is_(None))
        rows = list(session.exec(stmt).all())
        print(f"Found {len(rows)} transactions without embedding")

        if not rows:
            return

        to_embed: list[tuple[Transaction, str]] = []
        for t in rows:
            text = _build_search_text(t.merchant_name, t.note)
            if text:
                to_embed.append((t, text))

        print(f"Embedding {len(to_embed)} non-empty texts...")

        # Batch process
        for i in range(0, len(to_embed), BATCH_SIZE):
            batch = to_embed[i:i + BATCH_SIZE]
            texts = [text for _, text in batch]
            embeddings = client.embed_batch(texts)  # type: ignore[attr-defined]

            for (tx, _), emb in zip(batch, embeddings, strict=True):
                tx.search_embedding = emb
                session.add(tx)

            session.commit()
            print(f"  Processed {min(i + BATCH_SIZE, len(to_embed))}/{len(to_embed)}")

        print("Done.")


if __name__ == "__main__":
    backfill()
