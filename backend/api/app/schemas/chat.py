"""Chat schemas (Phase 6.7)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessageRequest(BaseModel):
    """Body cho POST /chat/message."""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=2000)
    conversation_id: int | None = Field(default=None, gt=0)


class ChatMessageItem(BaseModel):
    """Một message trong history response."""

    model_config = ConfigDict(extra="forbid")

    id: int
    conversation_id: int | None = None
    role: Literal["user", "assistant", "tool"]
    content: str | None
    tool_calls: list[dict[str, Any]] | None = None
    tool_name: str | None = None
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    """Response cho GET /chat/history."""

    model_config = ConfigDict(extra="forbid")

    items: list[ChatMessageItem]
    has_more: bool
    next_before_id: int | None = None


class ChatConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=255)


class ChatConversationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    title: str | None
    created_at: datetime
    updated_at: datetime
    message_count: int = Field(ge=0)
    last_message_at: datetime | None = None


class ChatConversationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ChatConversationResponse]
    has_more: bool
    next_before_id: int | None = None


class ChatConversationMessagesResponse(ChatHistoryResponse):
    conversation: ChatConversationResponse
