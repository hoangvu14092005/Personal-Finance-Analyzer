"""Insight provider adapters (Phase 6.4)."""
from __future__ import annotations

from app.services.insights.providers.base import (
    InsightProvider,
    InsightProviderError,
)
from app.services.insights.providers.factory import get_insight_provider
from app.services.insights.providers.mock import MockInsightProvider

__all__ = [
    "InsightProvider",
    "InsightProviderError",
    "MockInsightProvider",
    "get_insight_provider",
]
