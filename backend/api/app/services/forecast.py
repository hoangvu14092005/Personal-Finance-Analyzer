"""Predictive analytics — deterministic run-rate forecast (G3 Mục 2).

KHÔNG dùng ML. Dự báo dựa trên tốc độ chi tiêu hiện tại (run-rate), giải thích
được và ổn định cho dataset cá nhân:

- Dự báo chi cuối tháng = (đã chi trong tháng / số ngày đã qua) × tổng ngày tháng.
- Cảnh báo ngân sách: theo run-rate của từng category, dự báo có vượt budget
  trước cuối tháng không.

Tất cả đọc trực tiếp từ DB qua `analytics_queries` / `budgets` (real-time).
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from sqlmodel import Session

from app.services import analytics_queries as queries
from app.services.budgets import compute_budget_usage
from app.services.date_ranges import DateRange

ForecastBudgetStatus = Literal["on_track", "warning", "will_exceed", "exceeded"]


@dataclass(frozen=True, slots=True)
class MonthSpendForecast:
    """Dự báo tổng chi cho tháng hiện tại theo run-rate."""

    period_month: str
    days_elapsed: int
    days_in_month: int
    spent_so_far: Decimal
    daily_run_rate: Decimal
    projected_total: Decimal


@dataclass(frozen=True, slots=True)
class BudgetForecast:
    """Dự báo 1 budget có vượt trước cuối tháng không."""

    category_id: int
    category_name: str
    budget_amount: Decimal
    spent_so_far: Decimal
    projected_spend: Decimal
    projected_percent: float
    status: ForecastBudgetStatus
    projected_exceed_date: date | None  # ngày dự kiến chạm budget (None nếu không vượt)


@dataclass(frozen=True, slots=True)
class ForecastSummary:
    month: MonthSpendForecast
    budgets: list[BudgetForecast]


def _month_bounds(period_month: str) -> tuple[date, date]:
    year, month = (int(p) for p in period_month.split("-", 1))
    _, last_day = calendar.monthrange(year, month)
    return date(year, month, 1), date(year, month, last_day)


def _current_period_month(today: date) -> str:
    return f"{today.year:04d}-{today.month:02d}"


def compute_forecast(
    session: Session,
    user_id: int,
    *,
    today: date | None = None,
) -> ForecastSummary:
    """Dự báo chi tiêu + ngân sách cho tháng hiện tại theo run-rate.

    `today` cho phép test deterministic.
    """
    today = today or date.today()
    period_month = _current_period_month(today)
    first_day, last_day = _month_bounds(period_month)
    days_in_month = last_day.day
    # Số ngày đã qua tính cả hôm nay (tránh chia 0 ngày đầu tháng).
    days_elapsed = max(1, (today - first_day).days + 1)

    # Tổng chi từ đầu tháng tới hôm nay.
    spent_range = DateRange(start=first_day, end=today)
    spent_so_far, _ = queries.query_period_totals(session, user_id, spent_range)

    daily_rate = (spent_so_far / days_elapsed) if days_elapsed > 0 else Decimal("0")
    projected_total = (daily_rate * days_in_month).quantize(Decimal("1"))

    month = MonthSpendForecast(
        period_month=period_month,
        days_elapsed=days_elapsed,
        days_in_month=days_in_month,
        spent_so_far=spent_so_far,
        daily_run_rate=daily_rate.quantize(Decimal("1")),
        projected_total=projected_total,
    )

    budgets = _forecast_budgets(
        session,
        user_id,
        period_month=period_month,
        first_day=first_day,
        today=today,
        days_elapsed=days_elapsed,
        days_in_month=days_in_month,
    )

    return ForecastSummary(month=month, budgets=budgets)


def _forecast_budgets(
    session: Session,
    user_id: int,
    *,
    period_month: str,
    first_day: date,
    today: date,
    days_elapsed: int,
    days_in_month: int,
) -> list[BudgetForecast]:
    usages = compute_budget_usage(session, user_id, period_month)
    forecasts: list[BudgetForecast] = []
    for usage in usages:
        spent = usage.spent_amount
        daily_rate = (spent / days_elapsed) if days_elapsed > 0 else Decimal("0")
        projected = (daily_rate * days_in_month).quantize(Decimal("1"))
        budget_amount = usage.budget_amount
        projected_percent = (
            float(round((projected / budget_amount) * Decimal("100"), 2))
            if budget_amount > 0
            else 0.0
        )

        status: ForecastBudgetStatus
        exceed_date: date | None = None
        if spent > budget_amount:
            status = "exceeded"
        elif projected > budget_amount:
            status = "will_exceed"
            # Ước tính ngày chạm budget: budget / daily_rate (số ngày từ đầu tháng).
            if daily_rate > 0:
                days_to_hit = int(
                    (budget_amount / daily_rate).to_integral_value(rounding="ROUND_CEILING"),
                )
                day_index = min(max(days_to_hit, 1), days_in_month)
                exceed_date = first_day.replace(day=day_index)
        elif projected_percent >= 80.0:
            status = "warning"
        else:
            status = "on_track"

        forecasts.append(
            BudgetForecast(
                category_id=usage.category_id,
                category_name=usage.category_name,
                budget_amount=budget_amount,
                spent_so_far=spent,
                projected_spend=projected,
                projected_percent=projected_percent,
                status=status,
                projected_exceed_date=exceed_date,
            ),
        )
    return forecasts


__all__ = [
    "BudgetForecast",
    "ForecastSummary",
    "MonthSpendForecast",
    "compute_forecast",
]
