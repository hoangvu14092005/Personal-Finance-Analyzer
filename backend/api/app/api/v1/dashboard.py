"""Dashboard summary API (Phase 4.3).

Endpoint:
- `GET /api/v1/dashboard/summary?range=7d`
  - Query params:
    - `range`: preset key — "7d" | "30d" | "this_month" | "last_month" | "custom"
    - `start_date`, `end_date`: yêu cầu khi `range=custom` (ISO format YYYY-MM-DD)
    - `top_categories_limit`, `recent_transactions_limit`: optional, capped.
  - Trả `DashboardSummaryResponse` (current period + previous period + top
    categories + recent transactions). Frontend không tính business logic.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import User
from app.schemas.dashboard import (
    CategoryBreakdownResponse,
    DashboardSummaryResponse,
    PeriodTotalsResponse,
    RangeInfo,
    RecentTransactionResponse,
)
from app.services.analytics import (
    DEFAULT_RECENT_TRANSACTIONS_LIMIT,
    DEFAULT_TOP_CATEGORIES_LIMIT,
    compute_summary,
)
from app.services.date_ranges import (
    DateRange,
    InvalidDateRangeError,
    RangePreset,
    previous_period,
    resolve_range,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Cap limits để tránh client request quá nhiều rows một lúc.
MAX_TOP_CATEGORIES_LIMIT = 20
MAX_RECENT_TRANSACTIONS_LIMIT = 50


def _build_range_info(range_: DateRange, preset: RangePreset) -> RangeInfo:
    return RangeInfo(
        preset=preset.value,
        start=range_.start,
        end=range_.end,
        days=range_.days,
    )


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    name="dashboard_summary",
)
def get_dashboard_summary(
    range: str = Query(  # noqa: A002 - matching API contract
        "30d",
        description="Preset range: 7d | 30d | this_month | last_month | custom",
    ),
    start_date: date | None = Query(
        None,
        description="Required when range=custom (ISO date)",
    ),
    end_date: date | None = Query(
        None,
        description="Required when range=custom (ISO date)",
    ),
    top_categories_limit: int = Query(
        DEFAULT_TOP_CATEGORIES_LIMIT,
        ge=1,
        le=MAX_TOP_CATEGORIES_LIMIT,
        description="Số top categories trả về",
    ),
    recent_transactions_limit: int = Query(
        DEFAULT_RECENT_TRANSACTIONS_LIMIT,
        ge=1,
        le=MAX_RECENT_TRANSACTIONS_LIMIT,
        description="Số recent transactions trả về",
    ),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DashboardSummaryResponse:
    """Tính toán dashboard summary cho user hiện tại.

    Status code:
    - 200: trả payload bình thường (kể cả khi không có giao dịch — empty arrays).
    - 400: range preset không hợp lệ hoặc custom range thiếu start_date/end_date.
    - 401: chưa đăng nhập (xử lý ở `get_current_user`).
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )

    # Parse preset string → enum (raise 400 nếu invalid).
    try:
        preset = RangePreset(range)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid range preset: {range!r}. "
                f"Allowed: {[p.value for p in RangePreset]}"
            ),
        ) from exc

    # Resolve current + previous range (raise 400 nếu custom invalid).
    try:
        current_range = resolve_range(
            preset,
            custom_start=start_date,
            custom_end=end_date,
        )
    except InvalidDateRangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    previous_range = previous_period(current_range, preset)

    summary = compute_summary(
        session,
        current_user.id,
        current_range,
        previous_range,
        top_categories_limit=top_categories_limit,
        recent_transactions_limit=recent_transactions_limit,
    )

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
                category_id=cat.category_id,
                name=cat.name,
                color=cat.color,
                total_amount=cat.total_amount,
                transaction_count=cat.transaction_count,
                percentage=cat.percentage,
            )
            for cat in summary.top_categories
        ],
        recent_transactions=[
            RecentTransactionResponse(
                id=tx.id,
                merchant_name=tx.merchant_name,
                amount=tx.amount,
                currency=tx.currency,
                transaction_date=date.fromisoformat(tx.transaction_date),
                category_id=tx.category_id,
                category_name=tx.category_name,
            )
            for tx in summary.recent_transactions
        ],
    )
