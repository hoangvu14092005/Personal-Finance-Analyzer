"""Pydantic schemas cho Dashboard summary API (Phase 4.3)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RangeInfo(BaseModel):
    """Thông tin range để frontend label rõ kỳ đang xem."""

    model_config = ConfigDict(extra="forbid")

    preset: str  # "7d" | "30d" | "this_month" | "last_month" | "custom"
    start: date
    end: date
    days: int = Field(ge=1, description="Số ngày trong range, inclusive cả 2 đầu")


class CategoryBreakdownResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: int | None
    name: str
    color: str | None
    total_amount: Decimal
    transaction_count: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)


class RecentTransactionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    merchant_name: str | None
    amount: Decimal
    currency: str
    transaction_date: date
    category_id: int | None
    category_name: str | None


class PeriodTotalsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_spend: Decimal
    transaction_count: int = Field(ge=0)


class DashboardSummaryResponse(BaseModel):
    """Payload đầy đủ cho `/dashboard/summary` endpoint."""

    model_config = ConfigDict(extra="forbid")

    range: RangeInfo
    previous_range: RangeInfo
    current: PeriodTotalsResponse
    previous: PeriodTotalsResponse
    delta_amount: Decimal
    # `None` khi previous total = 0 (không thể tính %). UI render "—".
    delta_percent: float | None
    top_categories: list[CategoryBreakdownResponse]
    recent_transactions: list[RecentTransactionResponse]


__all__ = [
    "CategoryBreakdownResponse",
    "DashboardSummaryResponse",
    "PeriodTotalsResponse",
    "RangeInfo",
    "RecentTransactionResponse",
]
