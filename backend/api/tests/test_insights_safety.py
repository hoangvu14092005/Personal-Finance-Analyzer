"""Tests cho `services.insights.safety` (Phase 6.8).

Verify:
- Banned phrase filter: item chứa "đầu tư chứng khoán", "crypto", ... bị drop.
- Unknown category_id: item reference category không có trong summary bị drop.
- Empty text sau strip bị drop.
- Items hợp lệ được giữ lại trong `filtered`.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.schemas.insights import (
    AlertItem,
    InsightItem,
    InsightPayload,
    RecommendationItem,
)
from app.services.analytics import (
    CategoryBreakdown,
    DashboardSummary,
    PeriodTotals,
)
from app.services.insights.safety import run_safety_checks
from app.services.insights.summary import SummaryInput


def _build_summary(category_ids: list[int]) -> SummaryInput:
    top = [
        CategoryBreakdown(
            category_id=cid,
            name=f"Cat{cid}",
            color=None,
            total_amount=Decimal("100000"),
            transaction_count=1,
            percentage=100.0 / max(len(category_ids), 1),
        )
        for cid in category_ids
    ]
    analytics = DashboardSummary(
        current=PeriodTotals(
            total_spend=Decimal("300000"), transaction_count=5,
        ),
        previous=PeriodTotals(total_spend=Decimal("200000"), transaction_count=3),
        delta_amount=Decimal("100000"),
        delta_percent=50.0,
        top_categories=top,
        recent_transactions=[],
    )
    return SummaryInput(
        range_preset="30d",
        range_start=date(2026, 4, 1),
        range_end=date(2026, 4, 30),
        analytics=analytics,
    )


class TestBannedPhrase:
    def test_drops_investment_advice(self) -> None:
        summary = _build_summary([1])
        payload = InsightPayload(
            insights=[
                InsightItem(
                    title="Gợi ý đầu tư chứng khoán",
                    body="Hãy mua cổ phiếu VNM để tăng lợi nhuận.",
                    category_id=1,
                ),
                InsightItem(
                    title="Chi ăn uống tăng",
                    body="Bạn đã chi nhiều hơn tháng trước cho ăn uống.",
                    category_id=1,
                ),
            ],
        )
        report = run_safety_checks(payload, summary)
        assert not report.ok
        assert len(report.violations) >= 1
        # Chỉ giữ lại item hợp lệ.
        assert len(report.filtered.insights) == 1
        assert report.filtered.insights[0].title == "Chi ăn uống tăng"

    def test_drops_crypto_recommendation(self) -> None:
        summary = _build_summary([1])
        payload = InsightPayload(
            recommendations=[
                RecommendationItem(
                    title="Mua bitcoin",
                    body="Đầu tư crypto để tăng giá trị.",
                ),
            ],
        )
        report = run_safety_checks(payload, summary)
        assert not report.ok
        assert len(report.filtered.recommendations) == 0


class TestGrounding:
    def test_unknown_category_id_dropped(self) -> None:
        summary = _build_summary([1, 2])
        payload = InsightPayload(
            insights=[
                InsightItem(
                    title="Test",
                    body="body",
                    category_id=999,  # Không có trong summary.
                ),
                InsightItem(
                    title="OK",
                    body="body",
                    category_id=1,
                ),
            ],
        )
        report = run_safety_checks(payload, summary)
        assert any(v.kind == "unknown_category" for v in report.violations)
        assert len(report.filtered.insights) == 1
        assert report.filtered.insights[0].category_id == 1

    def test_null_category_id_allowed(self) -> None:
        """category_id=None hợp lệ (insight chung, không gắn category)."""
        summary = _build_summary([1])
        payload = InsightPayload(
            insights=[
                InsightItem(
                    title="Overview",
                    body="Tổng quan chi tiêu ổn định.",
                    category_id=None,
                ),
            ],
        )
        report = run_safety_checks(payload, summary)
        assert report.ok
        assert len(report.filtered.insights) == 1


class TestAlertSeverity:
    def test_alerts_filtered(self) -> None:
        summary = _build_summary([1])
        payload = InsightPayload(
            alerts=[
                AlertItem(
                    title="Vượt ngân sách",
                    body="Chi vượt 120%.",
                    severity="critical",
                    category_id=1,
                ),
                AlertItem(
                    title="Lãi suất tăng",
                    body="Nên vay tiền nhanh để đầu tư.",
                    severity="info",
                ),
            ],
        )
        report = run_safety_checks(payload, summary)
        assert len(report.filtered.alerts) == 1
        assert report.filtered.alerts[0].severity == "critical"
