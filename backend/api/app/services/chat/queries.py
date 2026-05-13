"""Chat query functions — tools cho LLM function calling (Phase 6.1).

Mỗi function:
- Nhận `session` + `user_id` bắt buộc (user isolation enforced).
- Trả về dict serializable (Decimal → str, date → ISO).
- Không raise exception khi không có data — trả empty/None có ý nghĩa.
- Tái sử dụng services sẵn có khi phù hợp.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlmodel import Session, col, func, select

from app.models.entities import Category, Transaction
from app.services.analytics import compute_summary
from app.services.budgets import compute_budget_usage
from app.services.date_ranges import (
    RangePreset,
    previous_period,
    resolve_range,
)


def _resolve_preset(preset: str) -> RangePreset:
    """Parse preset string → enum. Default 'this_month' nếu invalid."""
    try:
        return RangePreset(preset)
    except ValueError:
        return RangePreset.THIS_MONTH


def _decimal_str(value: Decimal) -> str:
    return f"{value:.2f}"


def _current_period_month() -> str:
    today = date.today()
    return f"{today.year:04d}-{today.month:02d}"


def query_spending_summary(
    session: Session,
    user_id: int,
    *,
    date_range: str = "this_month",
    category_name: str | None = None,
) -> dict[str, Any]:
    """Tổng chi tiêu + top categories trong khoảng thời gian.

    Returns dict với: total_spend, transaction_count, top_categories[], date_range info.
    """
    preset = _resolve_preset(date_range)
    current = resolve_range(preset)
    previous = previous_period(current, preset)
    summary = compute_summary(session, user_id, current, previous)

    top_cats = [
        {
            "name": c.name,
            "total": _decimal_str(c.total_amount),
            "count": c.transaction_count,
            "percentage": c.percentage,
        }
        for c in summary.top_categories
    ]

    # Filter by category_name nếu có
    if category_name:
        cat_lower = category_name.lower()
        filtered = [c for c in top_cats if cat_lower in str(c["name"]).lower()]
        if filtered:
            total_for_cat = sum(
                (Decimal(str(c["total"])) for c in filtered), Decimal("0"),
            )
            return {
                "total_spend": _decimal_str(total_for_cat),
                "transaction_count": sum(int(str(c["count"])) for c in filtered),
                "category": category_name,
                "period": f"{current.start.isoformat()} to {current.end.isoformat()}",
                "currency": "VND",
            }

    return {
        "total_spend": _decimal_str(summary.current.total_spend),
        "transaction_count": summary.current.transaction_count,
        "top_categories": top_cats[:5],
        "period": f"{current.start.isoformat()} to {current.end.isoformat()}",
        "currency": "VND",
    }


def search_transactions(
    session: Session,
    user_id: int,
    *,
    merchant: str | None = None,
    date_range: str | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    category_name: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Tìm kiếm giao dịch theo nhiều tiêu chí.

    Returns dict với: transactions[], total_count.
    """
    query = select(Transaction).where(Transaction.user_id == user_id)

    # Date range filter
    if date_range:
        preset = _resolve_preset(date_range)
        range_ = resolve_range(preset)
        query = query.where(Transaction.transaction_date >= range_.start)
        query = query.where(Transaction.transaction_date <= range_.end)

    # Merchant filter (LIKE with escaped wildcards)
    if merchant:
        escaped = merchant.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(col(Transaction.merchant_name).ilike(f"%{escaped}%"))

    # Amount range
    if amount_min is not None:
        query = query.where(Transaction.amount >= Decimal(str(amount_min)))
    if amount_max is not None:
        query = query.where(Transaction.amount <= Decimal(str(amount_max)))

    # Category filter by name (join)
    if category_name:
        cat_lower = category_name.lower()
        cat_ids_query = select(Category.id).where(
            func.lower(Category.name).contains(cat_lower),
        )
        query = query.where(col(Transaction.category_id).in_(cat_ids_query))

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = session.exec(count_query).one()

    # Fetch with limit
    query = query.order_by(
        col(Transaction.transaction_date).desc(),
        col(Transaction.id).desc(),
    ).limit(min(limit, 50))

    rows = session.exec(query).all()

    transactions = [
        {
            "id": t.id,
            "merchant_name": t.merchant_name,
            "amount": _decimal_str(t.amount),
            "currency": t.currency,
            "transaction_date": t.transaction_date.isoformat(),
            "note": t.note,
        }
        for t in rows
    ]

    return {
        "transactions": transactions,
        "total_count": int(total_count),
        "showing": len(transactions),
    }


def get_budget_status(
    session: Session,
    user_id: int,
    *,
    period_month: str | None = None,
) -> dict[str, Any]:
    """Trạng thái budget cho tháng chỉ định (default: tháng hiện tại).

    Returns dict với: budgets[], period_month.
    """
    period = period_month or _current_period_month()
    usages = compute_budget_usage(session, user_id, period)

    budgets = [
        {
            "category_name": u.category_name,
            "budget_amount": _decimal_str(u.budget_amount),
            "spent_amount": _decimal_str(u.spent_amount),
            "remaining": _decimal_str(u.remaining_amount),
            "percent_used": u.percent_used,
            "status": u.status,
        }
        for u in usages
    ]

    return {
        "budgets": budgets,
        "period_month": period,
        "total_budgets": len(budgets),
    }


def compare_periods(
    session: Session,
    user_id: int,
    *,
    period_a: str = "this_month",
    period_b: str = "last_month",
) -> dict[str, Any]:
    """So sánh chi tiêu giữa 2 khoảng thời gian.

    Returns dict với: period_a info, period_b info, delta.
    """
    preset_a = _resolve_preset(period_a)
    preset_b = _resolve_preset(period_b)

    range_a = resolve_range(preset_a)
    range_b = resolve_range(preset_b)

    prev_a = previous_period(range_a, preset_a)
    prev_b = previous_period(range_b, preset_b)

    summary_a = compute_summary(session, user_id, range_a, prev_a)
    summary_b = compute_summary(session, user_id, range_b, prev_b)

    delta = summary_a.current.total_spend - summary_b.current.total_spend
    if summary_b.current.total_spend > 0:
        delta_pct = float(
            round((delta / summary_b.current.total_spend) * Decimal("100"), 2),
        )
    else:
        delta_pct = None

    return {
        "period_a": {
            "label": period_a,
            "range": f"{range_a.start.isoformat()} to {range_a.end.isoformat()}",
            "total_spend": _decimal_str(summary_a.current.total_spend),
            "transaction_count": summary_a.current.transaction_count,
        },
        "period_b": {
            "label": period_b,
            "range": f"{range_b.start.isoformat()} to {range_b.end.isoformat()}",
            "total_spend": _decimal_str(summary_b.current.total_spend),
            "transaction_count": summary_b.current.transaction_count,
        },
        "delta_amount": _decimal_str(delta),
        "delta_percent": delta_pct,
        "currency": "VND",
    }


def get_top_merchants(
    session: Session,
    user_id: int,
    *,
    date_range: str = "this_month",
    limit: int = 10,
) -> dict[str, Any]:
    """Top merchants theo tổng chi tiêu.

    Returns dict với: merchants[], period.
    """
    preset = _resolve_preset(date_range)
    range_ = resolve_range(preset)

    statement = (
        select(
            Transaction.merchant_name,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
        .where(Transaction.merchant_name.is_not(None))  # type: ignore[union-attr]
        .where(Transaction.merchant_name != "")
        .group_by(Transaction.merchant_name)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(min(limit, 20))
    )

    rows = session.exec(statement).all()

    merchants = [
        {
            "merchant_name": row[0],
            "total_spend": _decimal_str(Decimal(str(row[1]))) if row[1] else "0.00",
            "transaction_count": int(row[2] or 0),
        }
        for row in rows
    ]

    return {
        "merchants": merchants,
        "period": f"{range_.start.isoformat()} to {range_.end.isoformat()}",
        "currency": "VND",
    }


def get_spending_by_day(
    session: Session,
    user_id: int,
    *,
    date_range: str = "this_month",
) -> dict[str, Any]:
    """Chi tiêu theo ngày trong khoảng thời gian.

    Returns dict với: days[], period, total.
    """
    preset = _resolve_preset(date_range)
    range_ = resolve_range(preset)

    statement = (
        select(
            Transaction.transaction_date,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
        .group_by(Transaction.transaction_date)
        .order_by(Transaction.transaction_date.asc())
    )

    rows = session.exec(statement).all()

    days = [
        {
            "date": row[0].isoformat() if row[0] else None,
            "total_spend": _decimal_str(Decimal(str(row[1]))) if row[1] else "0.00",
            "transaction_count": int(row[2] or 0),
        }
        for row in rows
    ]

    grand_total = sum((Decimal(str(d["total_spend"])) for d in days), Decimal("0"))

    return {
        "days": days,
        "period": f"{range_.start.isoformat()} to {range_.end.isoformat()}",
        "total_spend": _decimal_str(grand_total),
        "total_days_with_spending": len(days),
        "currency": "VND",
    }


def get_recent_transactions(
    session: Session,
    user_id: int,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """N giao dịch gần nhất của user.

    Returns dict với: transactions[], count.
    """
    capped_limit = min(limit, 50)

    statement = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(
            col(Transaction.transaction_date).desc(),
            col(Transaction.id).desc(),
        )
        .limit(capped_limit)
    )

    rows = session.exec(statement).all()

    transactions = [
        {
            "id": t.id,
            "merchant_name": t.merchant_name,
            "amount": _decimal_str(t.amount),
            "currency": t.currency,
            "transaction_date": t.transaction_date.isoformat(),
            "note": t.note,
        }
        for t in rows
    ]

    return {
        "transactions": transactions,
        "count": len(transactions),
    }


__all__ = [
    "compare_periods",
    "get_budget_status",
    "get_recent_transactions",
    "get_spending_by_day",
    "get_top_merchants",
    "query_spending_summary",
    "search_transactions",
]
