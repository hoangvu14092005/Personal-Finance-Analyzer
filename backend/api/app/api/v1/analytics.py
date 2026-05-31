"""Analytics APIs aligned with the 8-screen API mapping contract.

`/dashboard/summary` remains as a compatibility endpoint. New UI code should
prefer `/analytics/*`, where every money metric is computed from `transactions`.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import User
from app.schemas.analytics import (
    AnalyticsAnomaliesResponse,
    AnalyticsBudgetsResponse,
    AnalyticsCalendarResponse,
    AnalyticsCategoriesResponse,
    AnalyticsDiagnosticsResponse,
    AnalyticsForecastResponse,
    AnalyticsInsightFeedResponse,
    AnalyticsMerchantsResponse,
    AnalyticsProductsResponse,
    AnalyticsReceiptStatsResponse,
    AnalyticsRecurringResponse,
    AnalyticsTaxResponse,
    AnalyticsTrendsResponse,
    AnomalyResponse,
    BudgetForecastResponse,
    CalendarDayResponse,
    CalendarLegendResponse,
    CategoryDriverResponse,
    MerchantBreakdownResponse,
    MerchantContributionResponse,
    MonthSpendForecastResponse,
    ProductBreakdownResponse,
    RecurringItemResponse,
    SellerBreakdownResponse,
    TrendPointResponse,
)
from app.schemas.budgets import BudgetUsageResponse
from app.schemas.dashboard import (
    CategoryBreakdownResponse,
    DashboardSummaryResponse,
    PeriodTotalsResponse,
    RangeInfo,
    RecentTransactionResponse,
)
from app.schemas.insights import InsightResponse
from app.services.analytics import (
    DEFAULT_RECENT_TRANSACTIONS_LIMIT,
    DEFAULT_TOP_CATEGORIES_LIMIT,
    compute_calendar_days,
    compute_category_breakdown,
    compute_merchant_breakdown,
    compute_product_breakdown,
    compute_receipt_stats,
    compute_spending_anomalies,
    compute_spending_trends,
    compute_summary,
    compute_vat_summary,
)
from app.services.budgets import BudgetUsage, compute_budget_usage
from app.services.date_ranges import (
    DateRange,
    InvalidDateRangeError,
    RangePreset,
    previous_period,
    resolve_range,
    year_ago_period,
)
from app.services.diagnostics import compute_spending_diagnostics
from app.services.forecast import compute_forecast
from app.services.recurring import compute_fixed_vs_variable
from app.services.insights import (
    generate_rule_based_insights,
    insight_to_payload,
    list_insights_for_user,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])

MAX_TOP_CATEGORIES_LIMIT = 20
MAX_RECENT_TRANSACTIONS_LIMIT = 50
MAX_TOP_MERCHANTS_LIMIT = 20
MAX_ANOMALIES_LIMIT = 20
MAX_TOP_PRODUCTS_LIMIT = 50
MAX_TOP_SELLERS_LIMIT = 20


def _require_user_id(current_user: User) -> int:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return current_user.id


def _build_range_info(range_: DateRange, preset: RangePreset) -> RangeInfo:
    return RangeInfo(
        preset=preset.value,
        start=range_.start,
        end=range_.end,
        days=range_.days,
    )


def _resolve_requested_range(
    range: str,  # noqa: A002 - API contract uses `range`
    start_date: date | None,
    end_date: date | None,
) -> tuple[RangePreset, DateRange]:
    try:
        preset = RangePreset(range)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid range preset: {range!r}. "
                f"Allowed: {[preset.value for preset in RangePreset]}"
            ),
        ) from exc

    try:
        resolved = resolve_range(
            preset,
            custom_start=start_date,
            custom_end=end_date,
        )
    except InvalidDateRangeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return preset, resolved


def _resolve_budget_period(range_: DateRange, preset: RangePreset) -> str:
    if preset in (RangePreset.THIS_MONTH, RangePreset.LAST_MONTH):
        return f"{range_.start.year:04d}-{range_.start.month:02d}"
    return f"{range_.end.year:04d}-{range_.end.month:02d}"


def _usage_response(usage: BudgetUsage) -> BudgetUsageResponse:
    return BudgetUsageResponse(
        budget_id=usage.budget_id,
        category_id=usage.category_id,
        category_name=usage.category_name,
        category_color=usage.category_color,
        period_month=usage.period_month,
        budget_amount=usage.budget_amount,
        spent_amount=usage.spent_amount,
        remaining_amount=usage.remaining_amount,
        percent_used=usage.percent_used,
        status=usage.status,
    )


def _insight_response(payload: dict[str, object]) -> InsightResponse:
    return InsightResponse.model_validate(payload)


@router.get("/overview", response_model=DashboardSummaryResponse)
def get_analytics_overview(
    range: str = Query(  # noqa: A002 - matching API contract
        "30d",
        description="Preset range: 7d | 30d | this_month | last_month | custom",
    ),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    top_categories_limit: int = Query(
        DEFAULT_TOP_CATEGORIES_LIMIT,
        ge=1,
        le=MAX_TOP_CATEGORIES_LIMIT,
    ),
    recent_transactions_limit: int = Query(
        DEFAULT_RECENT_TRANSACTIONS_LIMIT,
        ge=1,
        le=MAX_RECENT_TRANSACTIONS_LIMIT,
    ),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DashboardSummaryResponse:
    """Overview dashboard summary under the canonical `/analytics` namespace."""
    user_id = _require_user_id(current_user)
    preset, current_range = _resolve_requested_range(range, start_date, end_date)
    previous_range = previous_period(current_range, preset)
    summary = compute_summary(
        session,
        user_id,
        current_range,
        previous_range,
        top_categories_limit=top_categories_limit,
        recent_transactions_limit=recent_transactions_limit,
    )
    budget_period = _resolve_budget_period(current_range, preset)
    budget_usages = compute_budget_usage(session, user_id, budget_period)

    return DashboardSummaryResponse(
        range=_build_range_info(current_range, preset),
        previous_range=_build_range_info(previous_range, preset),
        current=PeriodTotalsResponse(
            total_spend=summary.current.total_spend,
            transaction_count=summary.current.transaction_count,
        ),
        previous=PeriodTotalsResponse(
            total_spend=summary.previous.total_spend,
            transaction_count=summary.previous.transaction_count,
        ),
        delta_amount=summary.delta_amount,
        delta_percent=summary.delta_percent,
        top_categories=[
            CategoryBreakdownResponse(
                category_id=category.category_id,
                name=category.name,
                color=category.color,
                total_amount=category.total_amount,
                transaction_count=category.transaction_count,
                percentage=category.percentage,
            )
            for category in summary.top_categories
        ],
        recent_transactions=[
            RecentTransactionResponse(
                id=transaction.id,
                merchant_name=transaction.merchant_name,
                amount=transaction.amount,
                currency=transaction.currency,
                transaction_date=date.fromisoformat(transaction.transaction_date),
                category_id=transaction.category_id,
                category_name=transaction.category_name,
            )
            for transaction in summary.recent_transactions
        ],
        budget_period=budget_period,
        budgets_usage=[_usage_response(usage) for usage in budget_usages],
    )


@router.get("/categories", response_model=AnalyticsCategoriesResponse)
def get_analytics_categories(
    range: str = Query("30d"),  # noqa: A002
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(DEFAULT_TOP_CATEGORIES_LIMIT, ge=1, le=MAX_TOP_CATEGORIES_LIMIT),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnalyticsCategoriesResponse:
    user_id = _require_user_id(current_user)
    preset, current_range = _resolve_requested_range(range, start_date, end_date)
    categories = compute_category_breakdown(session, user_id, current_range, limit=limit)
    return AnalyticsCategoriesResponse(
        range=_build_range_info(current_range, preset),
        items=[
            CategoryBreakdownResponse(
                category_id=category.category_id,
                name=category.name,
                color=category.color,
                total_amount=category.total_amount,
                transaction_count=category.transaction_count,
                percentage=category.percentage,
            )
            for category in categories
        ],
    )


@router.get("/trends", response_model=AnalyticsTrendsResponse)
def get_analytics_trends(
    range: str = Query("30d"),  # noqa: A002
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    group_by: str = Query("day", pattern="^(day|week|month)$"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnalyticsTrendsResponse:
    user_id = _require_user_id(current_user)
    preset, current_range = _resolve_requested_range(range, start_date, end_date)
    points = compute_spending_trends(session, user_id, current_range, group_by=group_by)
    return AnalyticsTrendsResponse(
        range=_build_range_info(current_range, preset),
        group_by=group_by,
        points=[
            TrendPointResponse(
                period_start=point.period_start,
                period_end=point.period_end,
                amount=point.amount,
                transaction_count=point.transaction_count,
            )
            for point in points
        ],
    )


@router.get("/merchants", response_model=AnalyticsMerchantsResponse)
def get_analytics_merchants(
    range: str = Query("30d"),  # noqa: A002
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(10, ge=1, le=MAX_TOP_MERCHANTS_LIMIT),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnalyticsMerchantsResponse:
    user_id = _require_user_id(current_user)
    preset, current_range = _resolve_requested_range(range, start_date, end_date)
    merchants = compute_merchant_breakdown(session, user_id, current_range, limit=limit)
    return AnalyticsMerchantsResponse(
        range=_build_range_info(current_range, preset),
        items=[
            MerchantBreakdownResponse(
                merchant_name=merchant.merchant_name,
                total_amount=merchant.total_amount,
                transaction_count=merchant.transaction_count,
                percentage=merchant.percentage,
            )
            for merchant in merchants
        ],
    )


@router.get("/calendar", response_model=AnalyticsCalendarResponse)
def get_analytics_calendar(
    range: str = Query("90d"),  # noqa: A002
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnalyticsCalendarResponse:
    user_id = _require_user_id(current_user)
    preset, current_range = _resolve_requested_range(range, start_date, end_date)
    days = compute_calendar_days(session, user_id, current_range)
    return AnalyticsCalendarResponse(
        range=_build_range_info(current_range, preset),
        days=[
            CalendarDayResponse(
                date=day.date,
                amount=day.amount,
                transaction_count=day.transaction_count,
                intensity=day.intensity,
                top_category_name=day.top_category_name,
                is_unusual=day.is_unusual,
            )
            for day in days
        ],
        legend=CalendarLegendResponse(
            levels={
                "0": "no_spend",
                "1": "low",
                "2": "medium",
                "3": "high",
                "4": "unusual",
            },
        ),
    )


@router.get("/anomalies", response_model=AnalyticsAnomaliesResponse)
def get_analytics_anomalies(
    range: str = Query("30d"),  # noqa: A002
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(10, ge=1, le=MAX_ANOMALIES_LIMIT),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnalyticsAnomaliesResponse:
    user_id = _require_user_id(current_user)
    preset, current_range = _resolve_requested_range(range, start_date, end_date)
    anomalies = compute_spending_anomalies(session, user_id, current_range, limit=limit)
    return AnalyticsAnomaliesResponse(
        range=_build_range_info(current_range, preset),
        anomalies=[
            AnomalyResponse(
                id=item.id,
                type=item.type,
                severity=item.severity,
                title=item.title,
                transaction_id=item.transaction_id,
                merchant_name=item.merchant_name,
                transaction_date=item.transaction_date,
                amount=item.amount,
                baseline_amount=item.baseline_amount,
                reason=item.reason,
            )
            for item in anomalies
        ],
    )


@router.get("/budgets", response_model=AnalyticsBudgetsResponse)
def get_analytics_budgets(
    period_month: str = Query(
        ...,
        min_length=7,
        max_length=7,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
    ),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnalyticsBudgetsResponse:
    user_id = _require_user_id(current_user)
    usages = compute_budget_usage(session, user_id, period_month)
    total_budget = sum((usage.budget_amount for usage in usages), start=Decimal("0"))
    total_spent = sum((usage.spent_amount for usage in usages), start=Decimal("0"))
    remaining_amount = total_budget - total_spent
    return AnalyticsBudgetsResponse(
        period_month=period_month,
        total_budget=total_budget,
        total_spent=total_spent,
        remaining_amount=remaining_amount,
        exceeded_count=sum(1 for usage in usages if usage.status == "exceeded"),
        warning_count=sum(1 for usage in usages if usage.status == "warning"),
        budgets=[_usage_response(usage) for usage in usages],
    )


@router.get("/products", response_model=AnalyticsProductsResponse)
def get_analytics_products(
    range: str = Query("30d"),  # noqa: A002
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(20, ge=1, le=MAX_TOP_PRODUCTS_LIMIT),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnalyticsProductsResponse:
    """Top sản phẩm theo tổng chi, từ line items của hóa đơn đã confirm."""
    user_id = _require_user_id(current_user)
    preset, current_range = _resolve_requested_range(range, start_date, end_date)
    products = compute_product_breakdown(session, user_id, current_range, limit=limit)
    return AnalyticsProductsResponse(
        range=_build_range_info(current_range, preset),
        items=[
            ProductBreakdownResponse(
                item_name=product.item_name,
                total_amount=product.total_amount,
                total_quantity=product.total_quantity,
                line_count=product.line_count,
                percentage=product.percentage,
            )
            for product in products
        ],
    )


@router.get("/tax", response_model=AnalyticsTaxResponse)
def get_analytics_tax(
    range: str = Query("30d"),  # noqa: A002
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    sellers_limit: int = Query(10, ge=1, le=MAX_TOP_SELLERS_LIMIT),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnalyticsTaxResponse:
    """Tổng hợp VAT + top người bán từ hóa đơn đã confirm."""
    user_id = _require_user_id(current_user)
    preset, current_range = _resolve_requested_range(range, start_date, end_date)
    summary = compute_vat_summary(session, user_id, current_range, sellers_limit=sellers_limit)
    return AnalyticsTaxResponse(
        range=_build_range_info(current_range, preset),
        subtotal_before_tax=summary.subtotal_before_tax,
        total_tax=summary.total_tax,
        grand_total=summary.grand_total,
        invoice_count=summary.invoice_count,
        effective_tax_rate=summary.effective_tax_rate,
        top_sellers=[
            SellerBreakdownResponse(
                seller_name=seller.seller_name,
                seller_tax_id=seller.seller_tax_id,
                total_amount=seller.total_amount,
                invoice_count=seller.invoice_count,
                percentage=seller.percentage,
            )
            for seller in summary.top_sellers
        ],
    )


@router.get("/receipts-stats", response_model=AnalyticsReceiptStatsResponse)
def get_analytics_receipts_stats(
    range: str = Query("30d"),  # noqa: A002
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnalyticsReceiptStatsResponse:
    """Thống kê pipeline hóa đơn (upload/OCR/confirm) trong range."""
    user_id = _require_user_id(current_user)
    preset, current_range = _resolve_requested_range(range, start_date, end_date)
    stats = compute_receipt_stats(session, user_id, current_range)
    return AnalyticsReceiptStatsResponse(
        range=_build_range_info(current_range, preset),
        total_receipts=stats.total_receipts,
        ready_count=stats.ready_count,
        failed_count=stats.failed_count,
        pending_count=stats.pending_count,
        with_invoice_count=stats.with_invoice_count,
        confirmed_count=stats.confirmed_count,
        ocr_success_rate=stats.ocr_success_rate,
    )


@router.get("/diagnostics", response_model=AnalyticsDiagnosticsResponse)
def get_analytics_diagnostics(
    range: str = Query("30d"),  # noqa: A002
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    top_drivers: int = Query(5, ge=1, le=10),
    compare: str = Query(
        "previous_period",
        pattern="^(previous_period|year_ago)$",
        description="Mốc so sánh: previous_period (kỳ liền trước) | year_ago (cùng kỳ năm trước)",
    ),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnalyticsDiagnosticsResponse:
    """Phân rã nguyên nhân thay đổi chi tiêu so với kỳ trước (theo category + merchant)."""
    user_id = _require_user_id(current_user)
    preset, current_range = _resolve_requested_range(range, start_date, end_date)
    if compare == "year_ago":
        previous_range = year_ago_period(current_range)
    else:
        previous_range = previous_period(current_range, preset)
    diag = compute_spending_diagnostics(
        session, user_id, current_range, previous_range, top_drivers=top_drivers,
    )
    return AnalyticsDiagnosticsResponse(
        range=_build_range_info(current_range, preset),
        previous_range=_build_range_info(previous_range, preset),
        current_total=diag.current_total,
        previous_total=diag.previous_total,
        delta_amount=diag.delta_amount,
        delta_percent=diag.delta_percent,
        drivers=[
            CategoryDriverResponse(
                category_id=driver.category_id,
                category_name=driver.category_name,
                current_amount=driver.current_amount,
                previous_amount=driver.previous_amount,
                delta_amount=driver.delta_amount,
                delta_percent=driver.delta_percent,
                direction=driver.direction,
                top_merchants=[
                    MerchantContributionResponse(
                        merchant_name=m.merchant_name,
                        current_amount=m.current_amount,
                        previous_amount=m.previous_amount,
                        delta_amount=m.delta_amount,
                    )
                    for m in driver.top_merchants
                ],
            )
            for driver in diag.drivers
        ],
    )


@router.get("/forecast", response_model=AnalyticsForecastResponse)
def get_analytics_forecast(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnalyticsForecastResponse:
    """Dự báo chi tiêu cuối tháng + cảnh báo ngân sách theo run-rate hiện tại."""
    user_id = _require_user_id(current_user)
    forecast = compute_forecast(session, user_id)
    return AnalyticsForecastResponse(
        month=MonthSpendForecastResponse(
            period_month=forecast.month.period_month,
            days_elapsed=forecast.month.days_elapsed,
            days_in_month=forecast.month.days_in_month,
            spent_so_far=forecast.month.spent_so_far,
            daily_run_rate=forecast.month.daily_run_rate,
            projected_total=forecast.month.projected_total,
        ),
        budgets=[
            BudgetForecastResponse(
                category_id=b.category_id,
                category_name=b.category_name,
                budget_amount=b.budget_amount,
                spent_so_far=b.spent_so_far,
                projected_spend=b.projected_spend,
                projected_percent=b.projected_percent,
                status=b.status,
                projected_exceed_date=b.projected_exceed_date,
            )
            for b in forecast.budgets
        ],
    )


@router.get("/recurring", response_model=AnalyticsRecurringResponse)
def get_analytics_recurring(
    lookback_months: int = Query(6, ge=2, le=12),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnalyticsRecurringResponse:
    """Phân tách chi cố định (định kỳ) vs biến đổi theo cửa sổ nhìn lại."""
    user_id = _require_user_id(current_user)
    summary = compute_fixed_vs_variable(session, user_id, lookback_months=lookback_months)
    return AnalyticsRecurringResponse(
        lookback_months=summary.lookback_months,
        fixed_monthly_estimate=summary.fixed_monthly_estimate,
        variable_last_month=summary.variable_last_month,
        recurring_items=[
            RecurringItemResponse(
                merchant_name=item.merchant_name,
                months_active=item.months_active,
                avg_monthly_amount=item.avg_monthly_amount,
                last_amount=item.last_amount,
                last_date=item.last_date,
            )
            for item in summary.recurring_items
        ],
    )


@router.get("/insight-feed", response_model=AnalyticsInsightFeedResponse)
def get_analytics_insight_feed(
    range: str = Query("30d"),  # noqa: A002
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(6, ge=1, le=20),
    auto_generate: bool = Query(True),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnalyticsInsightFeedResponse:
    user_id = _require_user_id(current_user)
    preset, current_range = _resolve_requested_range(range, start_date, end_date)
    rows, _, _ = list_insights_for_user(
        session,
        user_id=user_id,
        status="active",
        limit=limit,
    )
    rows = [
        row
        for row in rows
        if row.range_start == current_range.start and row.range_end == current_range.end
    ]
    source = "stored"
    if not rows and auto_generate:
        rows = generate_rule_based_insights(
            session,
            user_id=user_id,
            range_=current_range,
            preset=preset,
            force_refresh=False,
        )[:limit]
        source = "generated"

    items = [_insight_response(insight_to_payload(row)) for row in rows[:limit]]
    return AnalyticsInsightFeedResponse(
        range=_build_range_info(current_range, preset),
        hero=items[0] if items else None,
        insights=items,
        source=source,
        meta={"auto_generate": auto_generate},
    )


__all__ = ["router"]
