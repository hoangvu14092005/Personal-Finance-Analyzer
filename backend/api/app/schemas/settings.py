"""Schemas for Settings APIs."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AnalyticsRange = Literal["7d", "30d", "this_month", "last_month"]


class FinanceSettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_currency: str
    timezone: str
    locale: str
    default_analytics_range: AnalyticsRange
    budget_month_start_day: int = Field(ge=1, le=28)
    number_format_locale: str
    show_decimals: bool
    updated_at: datetime


class FinanceSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_currency: str | None = Field(default=None, min_length=3, max_length=10)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    locale: str | None = Field(default=None, min_length=2, max_length=16)
    default_analytics_range: AnalyticsRange | None = None
    budget_month_start_day: int | None = Field(default=None, ge=1, le=28)
    number_format_locale: str | None = Field(default=None, min_length=2, max_length=16)
    show_decimals: bool | None = None

    @field_validator("default_currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("timezone", "locale", "number_format_locale")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class AISettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_ai_data_processing: bool
    auto_generate_insights: bool
    assistant_use_history: bool
    updated_at: datetime


class AISettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_ai_data_processing: bool | None = None
    auto_generate_insights: bool | None = None
    assistant_use_history: bool | None = None


class PrivacySettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_file_retention_days: int = Field(ge=1)
    raw_prompt_retention_days: int = Field(ge=1)
    updated_at: datetime


class PrivacySettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_file_retention_days: int | None = Field(default=None, ge=1, le=3650)
    raw_prompt_retention_days: int | None = Field(default=None, ge=1, le=3650)


class NotificationSettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email_notifications_enabled: bool
    push_notifications_enabled: bool
    budget_alerts_enabled: bool
    receipt_notifications_enabled: bool
    insight_notifications_enabled: bool
    updated_at: datetime


class NotificationSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email_notifications_enabled: bool | None = None
    push_notifications_enabled: bool | None = None
    budget_alerts_enabled: bool | None = None
    receipt_notifications_enabled: bool | None = None
    insight_notifications_enabled: bool | None = None


__all__ = [
    "AISettingsResponse",
    "AISettingsUpdate",
    "AnalyticsRange",
    "FinanceSettingsResponse",
    "FinanceSettingsUpdate",
    "NotificationSettingsResponse",
    "NotificationSettingsUpdate",
    "PrivacySettingsResponse",
    "PrivacySettingsUpdate",
]
