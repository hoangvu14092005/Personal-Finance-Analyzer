"""Embedding client cho worker (Phase 7 — RAG).

Copy của API's embedding_client — tránh cross-project imports.
Cần đồng bộ với `backend/api/app/services/chat/embedding_client.py`.
"""
from __future__ import annotations

import time
from functools import lru_cache

from pfa_shared.entities import EMBEDDING_DIMENSION
from pfa_shared.logging import get_logger

logger = get_logger("worker.embedding")

EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class LocalEmbeddingClient:
    """Local sentence-transformers client."""

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME) -> None:
        from sentence_transformers import SentenceTransformer

        start = time.perf_counter()
        self._model = SentenceTransformer(model_name)
        elapsed = time.perf_counter() - start

        actual_dim = self._model.get_sentence_embedding_dimension()
        if actual_dim != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Embedding dimension mismatch: {actual_dim} vs {EMBEDDING_DIMENSION}",
            )

        logger.info(
            "embedding.model_loaded name=%s dimension=%d load_time_s=%.1f",
            model_name, actual_dim, elapsed,
        )

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embed — sync version for worker."""
        if not texts:
            return []
        start = time.perf_counter()
        embeddings = self._model.encode(texts, show_progress_bar=False, batch_size=32)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "embedding.batch count=%d duration_ms=%.1f",
            len(texts), elapsed_ms,
        )
        return [e.tolist() for e in embeddings]


@lru_cache(maxsize=1)
def get_embedding_client() -> LocalEmbeddingClient:
    """Singleton embedding client."""
    return LocalEmbeddingClient()


__all__ = ["EMBEDDING_MODEL_NAME", "LocalEmbeddingClient", "get_embedding_client"]
