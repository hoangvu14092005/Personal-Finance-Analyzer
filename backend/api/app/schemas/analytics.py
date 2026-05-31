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


class ProductBreakdownResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_name: str
    total_amount: Decimal
    total_quantity: Decimal
    line_count: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)


class AnalyticsProductsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    range: RangeInfo
    items: list[ProductBreakdownResponse]


class SellerBreakdownResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seller_name: str
    seller_tax_id: str | None
    total_amount: Decimal
    invoice_count: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)


class AnalyticsTaxResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    range: RangeInfo
    subtotal_before_tax: Decimal
    total_tax: Decimal
    grand_total: Decimal
    invoice_count: int = Field(ge=0)
    effective_tax_rate: float = Field(ge=0)
    top_sellers: list[SellerBreakdownResponse]


class AnalyticsReceiptStatsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    range: RangeInfo
    total_receipts: int = Field(ge=0)
    ready_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    pending_count: int = Field(ge=0)
    with_invoice_count: int = Field(ge=0)
    confirmed_count: int = Field(ge=0)
    ocr_success_rate: float = Field(ge=0, le=100)


# --- Diagnostics (G3 Mục 1) ---


class MerchantContributionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merchant_name: str
    current_amount: Decimal
    previous_amount: Decimal
    delta_amount: Decimal


class CategoryDriverResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: int | None
    category_name: str
    current_amount: Decimal
    previous_amount: Decimal
    delta_amount: Decimal
    delta_percent: float | None
    direction: str
    top_merchants: list[MerchantContributionResponse]


class AnalyticsDiagnosticsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    range: RangeInfo
    previous_range: RangeInfo
    current_total: Decimal
    previous_total: Decimal
    delta_amount: Decimal
    delta_percent: float | None
    drivers: list[CategoryDriverResponse]


# --- Forecast (G3 Mục 2) ---


class MonthSpendForecastResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_month: str
    days_elapsed: int = Field(ge=0)
    days_in_month: int = Field(ge=1)
    spent_so_far: Decimal
    daily_run_rate: Decimal
    projected_total: Decimal


class BudgetForecastResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: int
    category_name: str
    budget_amount: Decimal
    spent_so_far: Decimal
    projected_spend: Decimal
    projected_percent: float = Field(ge=0)
    status: str
    projected_exceed_date: date | None


class AnalyticsForecastResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: MonthSpendForecastResponse
    budgets: list[BudgetForecastResponse]


__all__ = [
    "AnalyticsBudgetsResponse",
    "AnalyticsCategoriesResponse",
    "AnalyticsAnomaliesResponse",
    "AnalyticsCalendarResponse",
    "AnalyticsDiagnosticsResponse",
    "AnalyticsForecastResponse",
    "AnalyticsInsightFeedResponse",
    "AnalyticsMerchantsResponse",
    "AnalyticsProductsResponse",
    "AnalyticsReceiptStatsResponse",
    "AnalyticsTaxResponse",
    "AnalyticsTrendsResponse",
    "AnomalyResponse",
    "BudgetForecastResponse",
    "CalendarDayResponse",
    "CalendarLegendResponse",
    "CategoryDriverResponse",
    "MerchantBreakdownResponse",
    "MerchantContributionResponse",
    "MonthSpendForecastResponse",
    "ProductBreakdownResponse",
    "SellerBreakdownResponse",
    "TrendPointResponse",
]
