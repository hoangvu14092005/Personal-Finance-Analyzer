"""Schemas for user profile APIs."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    email: EmailStr
    full_name: str | None
    currency: str
    timezone: str
    locale: str
    is_active: bool
    created_at: datetime


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, max_length=255)
    currency: str | None = Field(default=None, min_length=3, max_length=10)
    timezone: str | None = Field(default=None, max_length=64)
    locale: str | None = Field(default=None, max_length=16)


__all__ = ["UserProfileResponse", "UserProfileUpdate"]
