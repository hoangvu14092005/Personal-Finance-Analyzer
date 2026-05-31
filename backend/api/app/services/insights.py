"""Row-level insight service.

Insights are narrative/cache rows backed by transaction/budget evidence. They are
not source-of-truth for money; evidence values are derived from SQL aggregates.
"""
from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlmodel import Session, col, select

from app.core.config import get_settings
from app.models.entities import Insight, InsightFeedback, UserSettings
from app.services import analytics_queries as queries
from app.services.analytics import compute_summary
from app.services.budgets import compute_budget_usage
from app.services.date_ranges import DateRange, RangePreset, previous_period, resolve_range
from app.services.diagnostics import compute_spending_diagnostics
from app.services.forecast import compute_forecast
from app.services.insight_narrator import narrate_insight
from pfa_shared.enums import AppEnv


class InsightNotFoundError(Exception):
    """Insight does not exist or is not owned by user."""


def _json_dumps(value: list[dict[str, Any]]) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _decimal_str(value: Decimal) -> str:
    return f"{value:.2f}"


def _user_allows_ai(session: Session, user_id: int) -> bool:
    """Đọc cờ allow_ai_data_processing. Mặc định True nếu chưa có settings row."""
    settings = session.exec(
        select(UserSettings).where(UserSettings.user_id == user_id),
    ).first()
    if settings is None:
        return True
    return settings.allow_ai_data_processing


def ensure_insight_owner(session: Session, *, insight_id: int, user_id: int) -> Insight:
    insight = session.get(Insight, insight_id)
    if insight is None or insight.user_id != user_id or insight.deleted_at is not None:
        raise InsightNotFoundError("Insight not found")
    return insight


def insight_to_payload(insight: Insight) -> dict[str, Any]:
    if insight.id is None:
        raise ValueError("Insight id missing")
    return {
        "id": insight.id,
        "type": insight.type,
        "severity": insight.severity,
        "title": insight.title,
        "summary": insight.summary,
        "evidence": _json_loads(insight.evidence_json),
        "actions": _json_loads(insight.actions_json),
        "range_start": insight.range_start,
        "range_end": insight.range_end,
        "status": insight.status,
        "dismissed_at": insight.dismissed_at,
        "created_at": insight.created_at,
        "updated_at": insight.updated_at,
    }


def list_insights_for_user(
    session: Session,
    *,
    user_id: int,
    status: str | None = None,
    type_filter: str | None = None,
    severity: str | None = None,
    limit: int = 20,
    before_id: int | None = None,
) -> tuple[list[Insight], bool, int | None]:
    statement = (
        select(Insight)
        .where(Insight.user_id == user_id)
        .where(Insight.deleted_at.is_(None))  # type: ignore[union-attr]
    )
    if status is not None:
        statement = statement.where(Insight.status == status)
    if type_filter is not None:
        statement = statement.where(Insight.type == type_filter)
    if severity is not None:
        statement = statement.where(Insight.severity == severity)
    if before_id is not None:
        statement = statement.where(col(Insight.id) < before_id)

    rows = list(
        session.exec(
            statement.order_by(col(Insight.created_at).desc(), col(Insight.id).desc()).limit(
                limit + 1,
            ),
        ).all(),
    )
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]
    next_before = rows[-1].id if has_more and rows else None
    return rows, has_more, next_before


def update_insight_status(
    session: Session,
    *,
    insight_id: int,
    user_id: int,
    status: str,
) -> Insight:
    insight = ensure_insight_owner(session, insight_id=insight_id, user_id=user_id)
    now = datetime.now(tz=UTC)
    insight.status = status
    insight.dismissed_at = now if status == "dismissed" else None
    insight.updated_at = now
    session.add(insight)
    session.commit()
    session.refresh(insight)
    return insight


def create_insight_feedback(
    session: Session,
    *,
    insight_id: int,
    user_id: int,
    rating: str,
    comment: str | None = None,
) -> InsightFeedback:
    ensure_insight_owner(session, insight_id=insight_id, user_id=user_id)
    feedback = InsightFeedback(
        insight_id=insight_id,
        user_id=user_id,
        rating=rating,
        comment=comment,
    )
    session.add(feedback)
    session.commit()
    session.refresh(feedback)
    return feedback


def _create_or_reuse_insight(
    session: Session,
    *,
    user_id: int,
    type_: str,
    severity: str,
    title: str,
    summary: str,
    evidence: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    range_: DateRange,
    force_refresh: bool,
) -> Insight:
    if not force_refresh:
        existing = session.exec(
            select(Insight)
            .where(Insight.user_id == user_id)
            .where(Insight.type == type_)
            .where(Insight.range_start == range_.start)
            .where(Insight.range_end == range_.end)
            .where(Insight.deleted_at.is_(None))  # type: ignore[union-attr]
            .order_by(col(Insight.created_at).desc(), col(Insight.id).desc()),
        ).first()
        if existing is not None:
            return existing

    # Narration LLM (B2) chỉ chạy khi tạo row MỚI (cache miss) → các request sau
    # tái dùng row đã narrate, không gọi lại LLM. Gated bởi cờ quyền riêng tư.
    # Bỏ qua trong môi trường test để giữ deterministic + không gọi mạng.
    final_title = title
    final_summary = summary
    if get_settings().app_env != AppEnv.TEST and _user_allows_ai(session, user_id):
        narrated = narrate_insight(
            insight_type=type_,
            base_title=title,
            base_summary=summary,
            evidence=evidence,
        )
        if narrated is not None:
            final_title = narrated.title
            final_summary = narrated.summary

    insight = Insight(
        user_id=user_id,
        type=type_,
        severity=severity,
        title=final_title,
        summary=final_summary,
        evidence_json=_json_dumps(evidence),
        actions_json=_json_dumps(actions),
        range_start=range_.start,
        range_end=range_.end,
        status="active",
    )
    session.add(insight)
    session.commit()
    session.refresh(insight)
    return insight


def generate_rule_based_insights(
    session: Session,
    *,
    user_id: int,
    range_: DateRange,
    preset: RangePreset,
    force_refresh: bool = False,
    types: list[str] | None = None,
) -> list[Insight]:
    """Generate deterministic MVP insights from transaction/budget evidence."""
    allowed_types = set(types or [])

    def wants(type_: str) -> bool:
        return not allowed_types or type_ in allowed_types

    previous = previous_period(range_, preset)
    summary = compute_summary(session, user_id, range_, previous)
    insights: list[Insight] = []

    if summary.current.transaction_count == 0 and wants("insufficient_data"):
        insights.append(
            _create_or_reuse_insight(
                session,
                user_id=user_id,
                type_="insufficient_data",
                severity="info",
                title="Chưa đủ dữ liệu chi tiêu",
                summary="Bạn chưa có giao dịch đã xác nhận trong khoảng thời gian này.",
                evidence=[
                    {
                        "source_type": "transactions",
                        "transaction_count": 0,
                        "range_start": range_.start.isoformat(),
                        "range_end": range_.end.isoformat(),
                    },
                ],
                actions=[{"type": "open_transactions", "label": "Thêm giao dịch"}],
                range_=range_,
                force_refresh=force_refresh,
            ),
        )
        return insights

    if summary.top_categories and wants("top_category"):
        top = summary.top_categories[0]
        severity = "watch" if top.percentage >= 50 else "info"
        insights.append(
            _create_or_reuse_insight(
                session,
                user_id=user_id,
                type_="top_category",
                severity=severity,
                title=f"{top.name} là danh mục chi nhiều nhất",
                summary=(
                    f"Bạn đã chi {_decimal_str(top.total_amount)} VND cho {top.name}, "
                    f"chiếm {top.percentage:.2f}% tổng chi trong kỳ."
                ),
                evidence=[
                    {
                        "source_type": "transactions",
                        "category_id": top.category_id,
                        "category_name": top.name,
                        "total_amount": _decimal_str(top.total_amount),
                        "transaction_count": top.transaction_count,
                        "percentage": top.percentage,
                    },
                ],
                actions=[
                    {
                        "type": "open_transactions",
                        "label": "Xem giao dịch",
                        "params": {"category_id": top.category_id},
                    },
                ],
                range_=range_,
                force_refresh=force_refresh,
            ),
        )

    if (
        summary.delta_percent is not None
        and abs(summary.delta_percent) >= 20
        and wants("period_change")
    ):
        direction = "tăng" if summary.delta_amount > 0 else "giảm"
        severity = "warning" if summary.delta_amount > 0 else "success"
        insights.append(
            _create_or_reuse_insight(
                session,
                user_id=user_id,
                type_="period_change",
                severity=severity,
                title=f"Chi tiêu {direction} {abs(summary.delta_percent):.2f}% so với kỳ trước",
                summary=(
                    f"Kỳ này tổng chi là {_decimal_str(summary.current.total_spend)} VND, "
                    f"chênh {_decimal_str(summary.delta_amount)} VND so với kỳ trước."
                ),
                evidence=[
                    {
                        "source_type": "transactions",
                        "current_total": _decimal_str(summary.current.total_spend),
                        "previous_total": _decimal_str(summary.previous.total_spend),
                        "delta_amount": _decimal_str(summary.delta_amount),
                        "delta_percent": summary.delta_percent,
                    },
                ],
                actions=[{"type": "open_analytics", "label": "Xem phân tích"}],
                range_=range_,
                force_refresh=force_refresh,
            ),
        )

    period_month = f"{range_.end.year:04d}-{range_.end.month:02d}"
    budget_usages = compute_budget_usage(session, user_id, period_month)
    exceeded = [usage for usage in budget_usages if usage.status == "exceeded"]
    if exceeded and wants("budget_exceeded"):
        usage = exceeded[0]
        insights.append(
            _create_or_reuse_insight(
                session,
                user_id=user_id,
                type_="budget_exceeded",
                severity="danger",
                title=f"{usage.category_name} đã vượt ngân sách",
                summary=(
                    f"Bạn đã dùng {usage.percent_used:.2f}% ngân sách {usage.category_name} "
                    f"trong {period_month}."
                ),
                evidence=[
                    {
                        "source_type": "budgets",
                        "budget_id": usage.budget_id,
                        "category_id": usage.category_id,
                        "category_name": usage.category_name,
                        "budget_amount": _decimal_str(usage.budget_amount),
                        "spent_amount": _decimal_str(usage.spent_amount),
                        "percent_used": usage.percent_used,
                    },
                ],
                actions=[{"type": "open_budgets", "label": "Xem ngân sách"}],
                range_=range_,
                force_refresh=force_refresh,
            ),
        )

    insights.extend(
        _generate_advanced_insights(
            session,
            user_id=user_id,
            range_=range_,
            preset=preset,
            force_refresh=force_refresh,
            wants=wants,
        ),
    )

    return insights


def _generate_advanced_insights(
    session: Session,
    *,
    user_id: int,
    range_: DateRange,
    preset: RangePreset,
    force_refresh: bool,
    wants: Any,
) -> list[Insight]:
    """Luật insight nâng cao (B1): cảnh báo sớm vượt ngân sách, danh mục tăng
    đột biến, merchant mới, chi cuối tuần cao. Tất cả deterministic từ aggregate.
    """
    out: list[Insight] = []

    # --- budget_projected_exceed: dự báo SẼ vượt trước khi vượt thật ---
    if wants("budget_projected_exceed"):
        forecast = compute_forecast(session, user_id)
        will_exceed = [b for b in forecast.budgets if b.status == "will_exceed"]
        if will_exceed:
            b = will_exceed[0]
            exceed_date = (
                b.projected_exceed_date.isoformat() if b.projected_exceed_date else None
            )
            out.append(
                _create_or_reuse_insight(
                    session,
                    user_id=user_id,
                    type_="budget_projected_exceed",
                    severity="warning",
                    title=f"{b.category_name} dự báo sẽ vượt ngân sách",
                    summary=(
                        f"Theo nhịp chi hiện tại, {b.category_name} dự kiến đạt "
                        f"{_decimal_str(b.projected_spend)} VND "
                        f"({b.projected_percent:.0f}% ngân sách) cuối tháng."
                        + (f" Dự kiến chạm hạn mức ngày {exceed_date}." if exceed_date else "")
                    ),
                    evidence=[
                        {
                            "source_type": "forecast",
                            "category_id": b.category_id,
                            "category_name": b.category_name,
                            "budget_amount": _decimal_str(b.budget_amount),
                            "spent_so_far": _decimal_str(b.spent_so_far),
                            "projected_spend": _decimal_str(b.projected_spend),
                            "projected_percent": b.projected_percent,
                            "projected_exceed_date": exceed_date,
                        },
                    ],
                    actions=[
                        {
                            "type": "open_budgets",
                            "label": "Xem ngân sách",
                            "params": {"category_id": b.category_id},
                        },
                    ],
                    range_=range_,
                    force_refresh=force_refresh,
                ),
            )

    # --- category_surge: 1 danh mục tăng mạnh so kỳ trước ---
    if wants("category_surge"):
        previous = previous_period(range_, preset)
        diag = compute_spending_diagnostics(
            session, user_id, range_, previous, top_drivers=3,
        )
        surge = next(
            (
                d
                for d in diag.drivers
                if d.direction == "increase"
                and d.previous_amount > 0
                and d.delta_percent is not None
                and d.delta_percent >= 50.0
            ),
            None,
        )
        if surge is not None:
            top_m = surge.top_merchants[0].merchant_name if surge.top_merchants else None
            out.append(
                _create_or_reuse_insight(
                    session,
                    user_id=user_id,
                    type_="category_surge",
                    severity="watch",
                    title=f"{surge.category_name} tăng mạnh so với kỳ trước",
                    summary=(
                        f"{surge.category_name} tăng {_decimal_str(surge.delta_amount)} VND "
                        f"(+{surge.delta_percent:.0f}%) so với kỳ trước."
                        + (f" Chủ yếu từ {top_m}." if top_m else "")
                    ),
                    evidence=[
                        {
                            "source_type": "diagnostics",
                            "category_id": surge.category_id,
                            "category_name": surge.category_name,
                            "current_amount": _decimal_str(surge.current_amount),
                            "previous_amount": _decimal_str(surge.previous_amount),
                            "delta_amount": _decimal_str(surge.delta_amount),
                            "delta_percent": surge.delta_percent,
                        },
                    ],
                    actions=[
                        {
                            "type": "open_transactions",
                            "label": "Xem giao dịch",
                            "params": {"category_id": surge.category_id},
                        },
                    ],
                    range_=range_,
                    force_refresh=force_refresh,
                ),
            )

    # --- new_merchant: merchant lần đầu xuất hiện trong kỳ ---
    if wants("new_merchant"):
        seen_before = queries.query_merchants_seen_before(
            session, user_id, before=range_.start,
        )
        current_merchants = queries.query_merchant_aggregates(
            session, user_id, range_, limit=20, exclude_unknown=True,
        )
        new_ones = [
            m
            for m in current_merchants
            if m.merchant_name.lower().strip() not in seen_before
        ]
        if new_ones:
            new_ones.sort(key=lambda m: m.total_amount, reverse=True)
            top = new_ones[0]
            extra = len(new_ones) - 1
            out.append(
                _create_or_reuse_insight(
                    session,
                    user_id=user_id,
                    type_="new_merchant",
                    severity="info",
                    title=f"Cửa hàng mới: {top.merchant_name}",
                    summary=(
                        f"Bạn lần đầu chi tại {top.merchant_name} "
                        f"({_decimal_str(top.total_amount)} VND) trong kỳ này."
                        + (f" Và {extra} cửa hàng mới khác." if extra > 0 else "")
                    ),
                    evidence=[
                        {
                            "source_type": "transactions",
                            "merchant_name": top.merchant_name,
                            "total_amount": _decimal_str(top.total_amount),
                            "transaction_count": top.transaction_count,
                            "new_merchant_count": len(new_ones),
                        },
                    ],
                    actions=[{"type": "open_transactions", "label": "Xem giao dịch"}],
                    range_=range_,
                    force_refresh=force_refresh,
                ),
            )

    # --- weekend_spike: chi cuối tuần/ngày cao hơn ngày thường rõ rệt ---
    if wants("weekend_spike"):
        wd_total, wd_days, we_total, we_days = queries.query_weekday_weekend_totals(
            session, user_id, range_,
        )
        if wd_days > 0 and we_days > 0:
            wd_avg = wd_total / wd_days
            we_avg = we_total / we_days
            if wd_avg > 0 and we_avg >= wd_avg * Decimal("1.5"):
                ratio = float(round((we_avg / wd_avg) * Decimal("100"), 0))
                out.append(
                    _create_or_reuse_insight(
                        session,
                        user_id=user_id,
                        type_="weekend_spike",
                        severity="info",
                        title="Chi cuối tuần cao hơn ngày thường",
                        summary=(
                            f"Trung bình mỗi ngày cuối tuần bạn chi "
                            f"{_decimal_str(we_avg)} VND, bằng {ratio:.0f}% so với "
                            f"ngày thường ({_decimal_str(wd_avg)} VND/ngày)."
                        ),
                        evidence=[
                            {
                                "source_type": "transactions",
                                "weekday_avg": _decimal_str(wd_avg),
                                "weekend_avg": _decimal_str(we_avg),
                                "weekday_days": wd_days,
                                "weekend_days": we_days,
                            },
                        ],
                        actions=[{"type": "open_analytics", "label": "Xem phân tích"}],
                        range_=range_,
                        force_refresh=force_refresh,
                    ),
                )

    return out


def resolve_insight_range(
    preset_value: str,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[RangePreset, DateRange]:
    preset = RangePreset(preset_value)
    return preset, resolve_range(preset, custom_start=start_date, custom_end=end_date)


__all__ = [
    "InsightNotFoundError",
    "create_insight_feedback",
    "ensure_insight_owner",
    "generate_rule_based_insights",
    "insight_to_payload",
    "list_insights_for_user",
    "resolve_insight_range",
    "update_insight_status",
]
