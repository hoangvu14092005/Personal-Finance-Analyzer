"""Factory cho InsightProvider (Phase 6.4).

Dispatch theo `settings.insight_provider`:
- "mock" → `MockInsightProvider`
- "ollama" → `OllamaInsightProvider(url, model, timeout)`
- "gemini" → `GeminiInsightProvider(api_key, model, timeout)`

Tách factory khỏi `__init__` để tránh eagerly instantiate provider khi
chỉ import type (vd. trong test).
"""
from __future__ import annotations

from app.core.config import Settings
from app.services.insights.providers.base import (
    InsightProvider,
    InsightProviderError,
)
from app.services.insights.providers.gemini import GeminiInsightProvider
from app.services.insights.providers.mock import MockInsightProvider
from app.services.insights.providers.ollama import OllamaInsightProvider


def get_insight_provider(settings: Settings) -> InsightProvider:
    """Return provider instance theo config. Raise khi config invalid."""
    kind = settings.insight_provider
    if kind == "mock":
        return MockInsightProvider()
    if kind == "ollama":
        return OllamaInsightProvider(
            base_url=settings.ollama_url,
            model=settings.ollama_model,
            timeout_seconds=settings.insight_request_timeout_seconds,
        )
    if kind == "gemini":
        if not settings.gemini_api_key:
            raise InsightProviderError(
                "insight_provider=gemini nhưng GEMINI_API_KEY chưa được set.",
            )
        return GeminiInsightProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            timeout_seconds=settings.insight_request_timeout_seconds,
        )
    # Pydantic Literal đã validate → không thể tới đây, nhưng defensive.
    raise InsightProviderError(f"Unknown insight_provider: {kind}")


__all__ = ["get_insight_provider"]
