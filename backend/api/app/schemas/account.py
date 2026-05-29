"""Schemas for account lifecycle APIs."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AccountDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=1000)


class AccountDeleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    requested_at: datetime | None
    scheduled_at: datetime | None
    cancelled_at: datetime | None
    message: str


__all__ = ["AccountDeleteRequest", "AccountDeleteResponse"]
