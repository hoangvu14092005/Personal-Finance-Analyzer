"""Phân tích chi cố định (định kỳ) vs biến đổi (C2).

Heuristic deterministic, không ML:
- Gom giao dịch theo merchant chuẩn hóa trong cửa sổ nhìn lại (mặc định 6 tháng).
- Một merchant được coi là "định kỳ" nếu xuất hiện ở >= `min_months` tháng
  RIÊNG BIỆT (đều đặn), gợi ý subscription/hóa đơn cố định.
- Số tiền cố định ước tính = trung vị số tiền theo tháng của merchant đó.
- Phần còn lại (không định kỳ) là chi biến đổi.

Đọc trực tiếp DB qua `analytics_queries` (real-time). VND-only.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlmodel import Session, col, func, select

from app.models.entities import Transaction
from app.services.date_ranges import DateRange

DEFAULT_LOOKBACK_MONTHS = 6
DEFAULT_MIN_MONTHS = 3


@dataclass(frozen=True, slots=True)
class RecurringItem:
    merchant_name: str
    months_active: int
    avg_monthly_amount: Decimal
    last_amount: Decimal
    last_date: date


@dataclass(frozen=True, slots=True)
class FixedVariableSummary:
    lookback_months: int
    fixed_monthly_estimate: Decimal  # tổng tiền cố định ước tính / tháng
    variable_last_month: Decimal     # chi biến đổi tháng gần nhất
    recurring_items: list[RecurringItem]


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _start_of_lookback(today: date, months: int) -> date:
    year = today.year
    month = today.month - (months - 1)
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def compute_fixed_vs_variable(
    session: Session,
    user_id: int,
    *,
    today: date | None = None,
    lookback_months: int = DEFAULT_LOOKBACK_MONTHS,
    min_months: int = DEFAULT_MIN_MONTHS,
) -> FixedVariableSummary:
    """Phân tách chi cố định/biến đổi trong cửa sổ nhìn lại."""
    today = today or date.today()
    start = _start_of_lookback(today, lookback_months)
    range_ = DateRange(start=start, end=today)

    rows = session.exec(
        select(
            func.coalesce(func.nullif(func.trim(Transaction.merchant_name), ""), "Không rõ"),
            Transaction.amount,
            Transaction.transaction_date,
        )
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
        .order_by(col(Transaction.transaction_date).asc()),
    ).all()

    # Gom theo merchant -> {month_key: tổng tiền tháng đó}
    by_merchant: dict[str, dict[str, Decimal]] = {}
    last_seen: dict[str, tuple[date, Decimal]] = {}
    for name, amount, tx_date in rows:
        merchant = str(name)
        amt = Decimal(str(amount))
        month = _month_key(tx_date)
        bucket = by_merchant.setdefault(merchant, {})
        bucket[month] = bucket.get(month, Decimal("0")) + amt
        prev = last_seen.get(merchant)
        if prev is None or tx_date >= prev[0]:
            last_seen[merchant] = (tx_date, amt)

    current_month = _month_key(today)
    recurring: list[RecurringItem] = []
    fixed_monthly = Decimal("0")
    recurring_merchants: set[str] = set()

    for merchant, months in by_merchant.items():
        if merchant == "Không rõ":
            continue
        if len(months) >= min_months:
            monthly_values = list(months.values())
            avg_monthly = Decimal(
                str(statistics.median(float(v) for v in monthly_values)),
            ).quantize(Decimal("1"))
            last_date, last_amount = last_seen[merchant]
            recurring.append(
                RecurringItem(
                    merchant_name=merchant,
                    months_active=len(months),
                    avg_monthly_amount=avg_monthly,
                    last_amount=last_amount,
                    last_date=last_date,
                ),
            )
            fixed_monthly += avg_monthly
            recurring_merchants.add(merchant)

    # Chi biến đổi tháng gần nhất = tổng giao dịch tháng hiện tại của merchant
    # KHÔNG thuộc nhóm định kỳ.
    variable_last = Decimal("0")
    for merchant, months in by_merchant.items():
        if merchant in recurring_merchants:
            continue
        variable_last += months.get(current_month, Decimal("0"))

    recurring.sort(key=lambda r: r.avg_monthly_amount, reverse=True)

    return FixedVariableSummary(
        lookback_months=lookback_months,
        fixed_monthly_estimate=fixed_monthly,
        variable_last_month=variable_last,
        recurring_items=recurring,
    )


__all__ = [
    "FixedVariableSummary",
    "RecurringItem",
    "compute_fixed_vs_variable",
]
