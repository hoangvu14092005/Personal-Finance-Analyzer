"""Schemas for lightweight security/session APIs."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SecuritySessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: int
    email: str
    is_current: bool
    created_at: datetime


class SecuritySessionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SecuritySessionResponse]


class LoginHistoryItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    occurred_at: datetime
    event: str
    ip_address: str | None = None
    user_agent: str | None = None


class LoginHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[LoginHistoryItemResponse]


__all__ = [
    "LoginHistoryItemResponse",
    "LoginHistoryResponse",
    "SecuritySessionListResponse",
    "SecuritySessionResponse",
]
