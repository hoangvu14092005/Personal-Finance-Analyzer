"""MockInsightProvider (Phase 6.4).

Rule-based provider — không gọi LLM thật, deterministic output dựa trên
SummaryInput. Dùng cho:
- MVP baseline (user chưa setup Ollama/Gemini vẫn chạy được Phase 6).
- Unit test (output predictable, fingerprint stable).
- CI environment (không cần external dep).

Rules (hiện tại):
1. Top category > 40% total → insight: "phụ thuộc nhiều vào X".
2. Delta ↑ >= 20% → alert warning: "chi tiêu tăng đáng kể".
3. Delta ↓ >= 10% → insight positive: "tiết kiệm hơn kỳ trước".
4. Budget exceeded → alert critical.
5. Budget warning (>=80%) → alert warning.
6. Anomaly transaction → recommendation "kiểm tra giao dịch lớn".
7. Không có alerts → recommendation generic cho top category.

Tất cả text phải match SummaryInput (không tự nghĩ ra số) → pass safety
grounding checks.
"""
from __future__ import annotations

from decimal import Decimal
from typing import ClassVar

from app.schemas.insights import (
    MAX_ALERTS,
    MAX_INSIGHTS,
    MAX_RECOMMENDATIONS,
    AlertItem,
    InsightItem,
    InsightPayload,
    RecommendationItem,
)
from app.services.insights.providers.base import InsightProvider
from app.services.insights.summary import SummaryInput


def _fmt_vnd(value: Decimal) -> str:
    """Format Decimal như "1.500.000 VND" — quen mắt với user VN."""
    # toLocaleString equivalent đơn giản: thousand separator bằng dấu chấm.
    whole = int(value)
    s = f"{whole:,}".replace(",", ".")
    return f"{s} VND"


class MockInsightProvider(InsightProvider):
    """Rule-based provider. Không cần network, không cần API key."""

    name: ClassVar[str] = "mock"

    # Ngưỡng để rule fire — có thể điều chỉnh.
    TOP_CATEGORY_DOMINANCE = 40.0  # % total_spend
    DELTA_UP_SIGNIFICANT = 20.0  # % delta tăng → warn
    DELTA_DOWN_SIGNIFICANT = 10.0  # % delta giảm → positive

    def generate(self, summary: SummaryInput) -> InsightPayload:
        insights: list[InsightItem] = []
        recommendations: list[RecommendationItem] = []
        alerts: list[AlertItem] = []

        self._rule_top_category(summary, insights)
        self._rule_delta(summary, insights, alerts)
        self._rule_budgets(summary, alerts, recommendations)
        self._rule_anomalies(summary, recommendations)
        self._rule_fallback_recommendation(summary, recommendations)

        # Clamp theo hard-limits của schema. Ưu tiên giữ những item quan
        # trọng ở đầu list → slice giữ nguyên thứ tự logic rule.
        return InsightPayload(
            insights=insights[:MAX_INSIGHTS],
            recommendations=recommendations[:MAX_RECOMMENDATIONS],
            alerts=alerts[:MAX_ALERTS],
        )

    def _rule_top_category(
        self,
        summary: SummaryInput,
        insights: list[InsightItem],
    ) -> None:
        if not summary.analytics.top_categories:
            return
        top = summary.analytics.top_categories[0]
        if top.percentage >= self.TOP_CATEGORY_DOMINANCE:
            insights.append(
                InsightItem(
                    title=f"{top.name} chiếm {top.percentage:.0f}% chi tiêu",
                    body=(
                        f"Bạn đã chi {_fmt_vnd(top.total_amount)} cho {top.name}"
                        f" ({top.transaction_count} giao dịch), chiếm"
                        f" {top.percentage:.0f}% tổng chi tiêu kỳ này."
                    ),
                    category_id=top.category_id,
                ),
            )

    def _rule_delta(
        self,
        summary: SummaryInput,
        insights: list[InsightItem],
        alerts: list[AlertItem],
    ) -> None:
        pct = summary.analytics.delta_percent
        if pct is None:
            return
        current = summary.analytics.current.total_spend
        previous = summary.analytics.previous.total_spend
        if pct >= self.DELTA_UP_SIGNIFICANT:
            alerts.append(
                AlertItem(
                    title=f"Chi tiêu tăng {pct:.0f}% so với kỳ trước",
                    body=(
                        f"Kỳ này bạn chi {_fmt_vnd(current)}, tăng"
                        f" {_fmt_vnd(summary.analytics.delta_amount)}"
                        f" ({pct:.0f}%) so với kỳ trước ({_fmt_vnd(previous)})."
                    ),
                    severity="warning",
                ),
            )
        elif pct <= -self.DELTA_DOWN_SIGNIFICANT:
            insights.append(
                InsightItem(
                    title=f"Chi tiêu giảm {abs(pct):.0f}% so với kỳ trước",
                    body=(
                        f"Kỳ này bạn chi {_fmt_vnd(current)}, giảm"
                        f" {_fmt_vnd(abs(summary.analytics.delta_amount))}"
                        f" ({abs(pct):.0f}%) so với kỳ trước. Tiếp tục duy trì."
                    ),
                ),
            )

    def _rule_budgets(
        self,
        summary: SummaryInput,
        alerts: list[AlertItem],
        recommendations: list[RecommendationItem],
    ) -> None:
        for b in summary.budgets:
            if b.status == "exceeded":
                over = b.spent_amount - b.budget_amount
                alerts.append(
                    AlertItem(
                        title=f"Vượt ngân sách {b.category_name}",
                        body=(
                            f"Đã chi {_fmt_vnd(b.spent_amount)} trên"
                            f" {_fmt_vnd(b.budget_amount)} ngân sách"
                            f" ({b.percent_used:.0f}%), vượt {_fmt_vnd(over)}."
                        ),
                        severity="critical",
                        category_id=b.category_id,
                    ),
                )
                recommendations.append(
                    RecommendationItem(
                        title=f"Giảm chi {b.category_name} kỳ tới",
                        body=(
                            f"Xem lại các giao dịch {b.category_name} để tìm"
                            f" khoản có thể cắt giảm."
                        ),
                        category_id=b.category_id,
                    ),
                )
            elif b.status == "warning":
                remaining = b.budget_amount - b.spent_amount
                alerts.append(
                    AlertItem(
                        title=f"Sắp vượt ngân sách {b.category_name}",
                        body=(
                            f"Đã dùng {b.percent_used:.0f}% ngân sách"
                            f" {b.category_name}, còn {_fmt_vnd(remaining)}"
                            f" để chi trong kỳ."
                        ),
                        severity="warning",
                        category_id=b.category_id,
                    ),
                )

    def _rule_anomalies(
        self,
        summary: SummaryInput,
        recommendations: list[RecommendationItem],
    ) -> None:
        if not summary.anomalies:
            return
        top = summary.anomalies[0]
        merchant = top.merchant_name or "Không rõ merchant"
        recommendations.append(
            RecommendationItem(
                title="Kiểm tra giao dịch lớn bất thường",
                body=(
                    f"Phát hiện giao dịch {_fmt_vnd(top.amount)} tại {merchant}"
                    f" ngày {top.transaction_date.isoformat()}. Hãy xác nhận"
                    f" khoản này có đúng mục đích không."
                ),
                category_id=top.category_id,
            ),
        )

    def _rule_fallback_recommendation(
        self,
        summary: SummaryInput,
        recommendations: list[RecommendationItem],
    ) -> None:
        # Nếu chưa có recommendation nào, thêm 1 rec cho top category để
        # UI không rỗng.
        if recommendations:
            return
        if not summary.analytics.top_categories:
            return
        top = summary.analytics.top_categories[0]
        recommendations.append(
            RecommendationItem(
                title=f"Đặt ngân sách cho {top.name}",
                body=(
                    f"{top.name} là danh mục chi lớn nhất"
                    f" ({top.percentage:.0f}%). Đặt ngân sách hàng tháng giúp"
                    f" bạn theo dõi và kiểm soát tốt hơn."
                ),
                category_id=top.category_id,
            ),
        )


__all__ = ["MockInsightProvider"]
