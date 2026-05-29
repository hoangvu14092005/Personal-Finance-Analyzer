"""Schemas for audit log APIs."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuditLogItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    event: str
    occurred_at: datetime
    actor_user_id: int
    target_type: str | None = None
    target_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AuditLogItemResponse]


__all__ = ["AuditLogItemResponse", "AuditLogResponse"]
