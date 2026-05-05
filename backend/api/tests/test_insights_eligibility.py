"""Tests cho `services.insights.eligibility` (Phase 6.2)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.analytics import (
    CategoryBreakdown,
    DashboardSummary,
    PeriodTotals,
    RecentTransactionItem,
)
from app.services.insights.eligibility import (
    MIN_DISTINCT_DAYS,
    MIN_TOTAL_SPEND,
    MIN_TRANSACTIONS,
    check_eligibility,
)
from app.services.insights.summary import SummaryInput


def _build_summary(
    *,
    txn_count: int,
    total_spend: Decimal,
    recent_dates: list[date] | None = None,
    top_categories: list[CategoryBreakdown] | None = None,
) -> SummaryInput:
    """Helper build SummaryInput minimal cho eligibility tests."""
    recent = [
        RecentTransactionItem(
            id=i,
            merchant_name=f"M{i}",
            amount=Decimal("10000"),
            currency="VND",
            transaction_date=d,
            category_id=None,
            category_name=None,
        )
        for i, d in enumerate(recent_dates or [], start=1)
    ]
    analytics = DashboardSummary(
        current=PeriodTotals(
            total_spend=total_spend, transaction_count=txn_count,
        ),
        previous=PeriodTotals(total_spend=Decimal("0"), transaction_count=0),
        delta_amount=total_spend,
        delta_percent=None,
        top_categories=top_categories or [],
        recent_transactions=recent,
    )
    return SummaryInput(
        range_preset="30d",
        range_start=date(2026, 4, 1),
        range_end=date(2026, 4, 30),
        analytics=analytics,
    )


class TestEligibility:
    def test_eligible_when_above_thresholds(self) -> None:
        summary = _build_summary(
            txn_count=MIN_TRANSACTIONS + 2,
            total_spend=MIN_TOTAL_SPEND + Decimal("100000"),
            recent_dates=[date(2026, 4, 1), date(2026, 4, 2), date(2026, 4, 3)],
        )
        result = check_eligibility(summary)
        assert result.eligible is True

    def test_too_few_transactions(self) -> None:
        summary = _build_summary(
            txn_count=MIN_TRANSACTIONS - 1,
            total_spend=MIN_TOTAL_SPEND + Decimal("100000"),
            recent_dates=[date(2026, 4, 1)],
        )
        result = check_eligibility(summary)
        assert result.eligible is False
        assert result.reason_code == "too_few_transactions"

    def test_too_low_spend(self) -> None:
        summary = _build_summary(
            txn_count=MIN_TRANSACTIONS + 2,
            total_spend=MIN_TOTAL_SPEND - Decimal("1"),
            recent_dates=[date(2026, 4, 1), date(2026, 4, 2), date(2026, 4, 3)],
        )
        result = check_eligibility(summary)
        assert result.eligible is False
        assert result.reason_code == "too_low_spend"

    def test_too_concentrated(self) -> None:
        """Tất cả giao dịch cùng 1 ngày → too_concentrated."""
        assert MIN_DISTINCT_DAYS >= 2
        summary = _build_summary(
            txn_count=MIN_TRANSACTIONS + 1,
            total_spend=MIN_TOTAL_SPEND + Decimal("100000"),
            # Chỉ 1 distinct date → distinct_days = 1 < 2.
            recent_dates=[
                date(2026, 4, 1),
                date(2026, 4, 1),
                date(2026, 4, 1),
                date(2026, 4, 1),
            ],
        )
        result = check_eligibility(summary)
        assert result.eligible is False
        assert result.reason_code == "too_concentrated"
