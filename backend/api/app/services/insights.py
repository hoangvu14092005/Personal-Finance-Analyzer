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

from app.models.entities import Insight, InsightFeedback
from app.services.analytics import compute_summary
from app.services.budgets import compute_budget_usage
from app.services.date_ranges import DateRange, RangePreset, previous_period, resolve_range


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

    insight = Insight(
        user_id=user_id,
        type=type_,
        severity=severity,
        title=title,
        summary=summary,
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

    return insights


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
