"""Schemas cho Category endpoint (Phase 3.4 / 3.6 supporting M4 UI).

Frontend cần list categories để render dropdown cho review form và manual
entry form. Endpoint trả combined system + user-owned categories.

G1: thêm CRUD cho category của user (create/update/delete).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    color: str | None = Field(default=None, max_length=20)


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, max_length=20)

