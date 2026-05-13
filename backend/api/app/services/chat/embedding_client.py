"""Embedding client (Phase 7 — RAG).

Wrap sentence-transformers model để embed tiếng Việt.
Model load 1 lần (lru_cache) để tránh load lại mỗi request.
"""
from __future__ import annotations

import asyncio
import time
from functools import lru_cache
from typing import Protocol

from pfa_shared.entities import EMBEDDING_DIMENSION

from app.core.logging import get_logger

logger = get_logger("api.chat.embedding")

EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class EmbeddingClient(Protocol):
    """Protocol cho embedding client — có thể swap provider (local / API)."""

    def embed_sync(self, text: str) -> list[float]: ...

    async def embed(self, text: str) -> list[float]: ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class LocalEmbeddingClient:
    """Local sentence-transformers client.

    Model load lazy ở __init__ (lần đầu ~30s để download + load).
    Sau đó encode nhanh ~20-50ms/text trên CPU.
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME) -> None:
        from sentence_transformers import SentenceTransformer

        start = time.perf_counter()
        self._model = SentenceTransformer(model_name)
        elapsed = time.perf_counter() - start

        # Verify dimension khớp với entity
        actual_dim = self._model.get_sentence_embedding_dimension()
        if actual_dim != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Embedding dimension mismatch: model returns {actual_dim}, "
                f"entity expects {EMBEDDING_DIMENSION}",
            )

        logger.info(
            "embedding.model_loaded name=%s dimension=%d load_time_s=%.1f",
            model_name, actual_dim, elapsed,
        )

    def embed_sync(self, text: str) -> list[float]:
        """Sync embed — dùng trong SQL transaction (vd: transaction create)."""
        start = time.perf_counter()
        embedding = self._model.encode(text, show_progress_bar=False)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug(
            "embedding.embed_sync len=%d duration_ms=%.1f",
            len(text), elapsed_ms,
        )
        return embedding.tolist()

    async def embed(self, text: str) -> list[float]:
        """Async embed — offload CPU work sang thread pool."""
        return await asyncio.to_thread(self.embed_sync, text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embed — hiệu quả hơn khi index nhiều chunks cùng lúc."""
        if not texts:
            return []

        start = time.perf_counter()
        embeddings = await asyncio.to_thread(
            self._model.encode, texts, show_progress_bar=False, batch_size=32,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "embedding.batch count=%d duration_ms=%.1f per_text_ms=%.1f",
            len(texts), elapsed_ms, elapsed_ms / len(texts),
        )
        return [e.tolist() for e in embeddings]


@lru_cache(maxsize=1)
def get_embedding_client() -> EmbeddingClient:
    """Singleton embedding client. Load model 1 lần."""
    return LocalEmbeddingClient()


__all__ = [
    "EMBEDDING_MODEL_NAME",
    "EmbeddingClient",
    "LocalEmbeddingClient",
    "get_embedding_client",
]
