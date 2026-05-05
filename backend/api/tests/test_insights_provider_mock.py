"""Tests cho `MockInsightProvider` (Phase 6.4).

Verify các rule fire đúng:
- Top category > 40% → insight dominance.
- Delta ↑ 20% → alert warning.
- Delta ↓ 10% → insight positive.
- Budget exceeded/warning → alert.
- Anomaly → recommendation.
- Fallback recommendation khi không có gì khác.
- Output luôn pass Pydantic schema + safety grounding.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.analytics import (
    CategoryBreakdown,
    DashboardSummary,
    PeriodTotals,
)
from app.services.budgets import BudgetUsage
from app.services.insights.providers.mock import MockInsightProvider
from app.services.insights.safety import run_safety_checks
from app.services.insights.summary import AnomalyCandidate, SummaryInput


def _build(
    *,
    top: list[CategoryBreakdown] | None = None,
    budgets: list[BudgetUsage] | None = None,
    anomalies: list[AnomalyCandidate] | None = None,
    current_total: str = "500000",
    previous_total: str = "400000",
    delta_pct: float | None = 25.0,
) -> SummaryInput:
    analytics = DashboardSummary(
        current=PeriodTotals(
            total_spend=Decimal(current_total), transaction_count=10,
        ),
        previous=PeriodTotals(
            total_spend=Decimal(previous_total), transaction_count=8,
        ),
        delta_amount=Decimal(current_total) - Decimal(previous_total),
        delta_percent=delta_pct,
        top_categories=top or [],
        recent_transactions=[],
    )
    return SummaryInput(
        range_preset="30d",
        range_start=date(2026, 4, 1),
        range_end=date(2026, 4, 30),
        analytics=analytics,
        budgets=budgets or [],
        anomalies=anomalies or [],
    )


class TestMockProviderRules:
    def test_top_category_dominance(self) -> None:
        summary = _build(
            top=[
                CategoryBreakdown(
                    category_id=1,
                    name="Ăn uống",
                    color=None,
                    total_amount=Decimal("500000"),
                    transaction_count=10,
                    percentage=60.0,
                ),
            ],
            delta_pct=5.0,  # Không đủ ngưỡng delta.
        )
        payload = MockInsightProvider().generate(summary)
        assert any("Ăn uống" in item.title for item in payload.insights)

    def test_delta_up_triggers_alert(self) -> None:
        summary = _build(delta_pct=30.0)
        payload = MockInsightProvider().generate(summary)
        assert len(payload.alerts) >= 1
        alert = payload.alerts[0]
        assert alert.severity in {"warning", "critical"}

    def test_delta_down_triggers_positive_insight(self) -> None:
        summary = _build(
            current_total="300000",
            previous_total="500000",
            delta_pct=-40.0,
        )
        payload = MockInsightProvider().generate(summary)
        assert any("giảm" in item.title.lower() for item in payload.insights)

    def test_budget_exceeded_alerts(self) -> None:
        budget = BudgetUsage(
            budget_id=1,
            category_id=1,
            category_name="Ăn uống",
            category_color=None,
            period_month="2026-04",
            budget_amount=Decimal("1000000"),
            spent_amount=Decimal("1200000"),
            remaining_amount=Decimal("-200000"),
            percent_used=120.0,
            status="exceeded",
        )
        summary = _build(budgets=[budget], delta_pct=5.0)
        payload = MockInsightProvider().generate(summary)
        assert any(a.severity == "critical" for a in payload.alerts)
        # Rec should mention reducing spend.
        assert any("Ăn uống" in r.title for r in payload.recommendations)

    def test_budget_warning_yields_alert(self) -> None:
        budget = BudgetUsage(
            budget_id=1,
            category_id=1,
            category_name="Ăn uống",
            category_color=None,
            period_month="2026-04",
            budget_amount=Decimal("1000000"),
            spent_amount=Decimal("850000"),
            remaining_amount=Decimal("150000"),
            percent_used=85.0,
            status="warning",
        )
        summary = _build(budgets=[budget], delta_pct=5.0)
        payload = MockInsightProvider().generate(summary)
        assert any(a.severity == "warning" for a in payload.alerts)

    def test_anomaly_rec(self) -> None:
        anomaly = AnomalyCandidate(
            kind="large_transaction",
            transaction_id=42,
            amount=Decimal("2000000"),
            transaction_date=date(2026, 4, 15),
            merchant_name="Best Buy",
            category_id=1,
        )
        summary = _build(anomalies=[anomaly], delta_pct=5.0)
        payload = MockInsightProvider().generate(summary)
        assert any("bất thường" in r.title.lower() for r in payload.recommendations)

    def test_fallback_recommendation(self) -> None:
        """Không có alerts/anomaly + có top category → recommend đặt ngân sách."""
        summary = _build(
            top=[
                CategoryBreakdown(
                    category_id=1,
                    name="Ăn uống",
                    color=None,
                    total_amount=Decimal("200000"),
                    transaction_count=5,
                    percentage=35.0,  # dưới threshold dominance.
                ),
            ],
            delta_pct=5.0,
        )
        payload = MockInsightProvider().generate(summary)
        assert len(payload.recommendations) >= 1


class TestMockProviderSafety:
    def test_output_grounded(self) -> None:
        """Mock output không bao giờ vi phạm safety checks."""
        summary = _build(
            top=[
                CategoryBreakdown(
                    category_id=1,
                    name="Ăn uống",
                    color=None,
                    total_amount=Decimal("500000"),
                    transaction_count=10,
                    percentage=60.0,
                ),
            ],
            delta_pct=30.0,
        )
        payload = MockInsightProvider().generate(summary)
        report = run_safety_checks(payload, summary)
        assert report.ok, f"violations: {report.violations}"
