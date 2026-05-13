"""Chat schemas (Phase 6.7)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """Body cho POST /chat/message."""

    content: str = Field(min_length=1, max_length=2000)


class ChatMessageItem(BaseModel):
    """Một message trong history response."""

    id: int
    role: Literal["user", "assistant", "tool"]
    content: str | None
    tool_calls: list[dict[str, Any]] | None = None
    tool_name: str | None = None
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    """Response cho GET /chat/history."""

    items: list[ChatMessageItem]
    has_more: bool
    next_before_id: int | None = None
