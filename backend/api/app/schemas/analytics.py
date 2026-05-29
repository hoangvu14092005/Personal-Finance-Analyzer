"""Pydantic schemas for `/api/v1/analytics/*` endpoints."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.budgets import BudgetUsageResponse
from app.schemas.dashboard import CategoryBreakdownResponse, RangeInfo
from app.schemas.insights import InsightResponse


class AnalyticsCategoriesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    range: RangeInfo
    items: list[CategoryBreakdownResponse]


class MerchantBreakdownResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merchant_name: str
    total_amount: Decimal
    transaction_count: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)


class AnalyticsMerchantsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    range: RangeInfo
    items: list[MerchantBreakdownResponse]


class AnalyticsBudgetsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_month: str
    total_budget: Decimal
    total_spent: Decimal
    remaining_amount: Decimal
    exceeded_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    budgets: list[BudgetUsageResponse]


class TrendPointResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_start: date
    period_end: date
    amount: Decimal
    transaction_count: int = Field(ge=0)


class AnalyticsTrendsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    range: RangeInfo
    group_by: str
    points: list[TrendPointResponse]


class CalendarDayResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    amount: Decimal
    transaction_count: int = Field(ge=0)
    intensity: int = Field(ge=0, le=4)
    top_category_name: str | None
    is_unusual: bool


class CalendarLegendResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    levels: dict[str, str]


class AnalyticsCalendarResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    range: RangeInfo
    days: list[CalendarDayResponse]
    legend: CalendarLegendResponse


class AnomalyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    severity: str
    title: str
    transaction_id: int
    merchant_name: str | None
    transaction_date: date
    amount: Decimal
    baseline_amount: Decimal
    reason: str


class AnalyticsAnomaliesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    range: RangeInfo
    anomalies: list[AnomalyResponse]


class AnalyticsInsightFeedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    range: RangeInfo
    hero: InsightResponse | None
    insights: list[InsightResponse]
    source: str
    meta: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "AnalyticsBudgetsResponse",
    "AnalyticsCategoriesResponse",
    "AnalyticsAnomaliesResponse",
    "AnalyticsCalendarResponse",
    "AnalyticsInsightFeedResponse",
    "AnalyticsMerchantsResponse",
    "AnalyticsTrendsResponse",
    "AnomalyResponse",
    "CalendarDayResponse",
    "CalendarLegendResponse",
    "MerchantBreakdownResponse",
    "TrendPointResponse",
]
