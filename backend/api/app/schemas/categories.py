"""Schemas cho Category endpoint (Phase 3.4 / 3.6 supporting M4 UI).

Frontend cần list categories để render dropdown cho review form và manual
entry form. Endpoint trả combined system + user-owned categories.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CategoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    name: str
    color: str | None
    is_system: bool
    user_id: int | None
    created_at: datetime


class CategoryListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CategoryResponse]
