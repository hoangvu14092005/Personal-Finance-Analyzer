"""Diagnostic analytics — phân rã nguyên nhân thay đổi chi tiêu (G3 Mục 1).

Trả lời "vì sao kỳ này chi nhiều/ít hơn kỳ trước": so sánh chi theo category giữa
2 kỳ, tìm các category thay đổi mạnh nhất, rồi drill-down merchant nào trong
category đó gây ra thay đổi.

Deterministic, đọc trực tiếp qua `analytics_queries` (real-time). Không LLM.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlmodel import Session, col, select

from app.models.entities import Category
from app.services import analytics_queries as queries
from app.services.date_ranges import DateRange

# Ngưỡng coi là "thay đổi đáng kể" để đưa vào diagnostics (VND tuyệt đối).
MIN_ABS_DELTA = Decimal("1")


@dataclass(frozen=True, slots=True)
class MerchantContribution:
    merchant_name: str
    current_amount: Decimal
    previous_amount: Decimal
    delta_amount: Decimal


@dataclass(frozen=True, slots=True)
class CategoryDriver:
    """Một category đóng góp vào thay đổi tổng chi."""

    category_id: int | None
    category_name: str
    current_amount: Decimal
    previous_amount: Decimal
    delta_amount: Decimal
    delta_percent: float | None  # None nếu previous=0
    direction: str  # "increase" | "decrease"
    top_merchants: list[MerchantContribution]


@dataclass(frozen=True, slots=True)
class SpendingDiagnostics:
    current_total: Decimal
    previous_total: Decimal
    delta_amount: Decimal
    delta_percent: float | None
    drivers: list[CategoryDriver]


def _category_name_map(session: Session, category_ids: set[int]) -> dict[int, str]:
    if not category_ids:
        return {}
    rows = session.exec(select(Category).where(col(Category.id).in_(category_ids))).all()
    return {c.id: c.name for c in rows if c.id is not None}


def compute_spending_diagnostics(
    session: Session,
    user_id: int,
    current: DateRange,
    previous: DateRange,
    *,
    top_drivers: int = 5,
    merchants_per_driver: int = 3,
) -> SpendingDiagnostics:
    """Phân rã thay đổi chi tiêu giữa `current` và `previous` theo category.

    Trả về các category thay đổi mạnh nhất (theo |delta|), mỗi cái kèm merchant
    đóng góp chính ở kỳ hiện tại.
    """
    cur_rows = queries.query_category_aggregates(session, user_id, current)
    prev_rows = queries.query_category_aggregates(session, user_id, previous)

    cur_by_cat: dict[int | None, Decimal] = {r.category_id: r.total_amount for r in cur_rows}
    prev_by_cat: dict[int | None, Decimal] = {r.category_id: r.total_amount for r in prev_rows}

    current_total = sum(cur_by_cat.values(), Decimal("0"))
    previous_total = sum(prev_by_cat.values(), Decimal("0"))
    delta_total = current_total - previous_total
    delta_pct = (
        float(round((delta_total / previous_total) * Decimal("100"), 2))
        if previous_total > 0
        else None
    )

    # Tên category (gộp id của cả 2 kỳ).
    cat_ids = {cid for cid in (cur_by_cat.keys() | prev_by_cat.keys()) if cid is not None}
    name_map = _category_name_map(session, cat_ids)

    # Tính delta theo từng category.
    all_cats = cur_by_cat.keys() | prev_by_cat.keys()
    deltas: list[tuple[int | None, Decimal, Decimal, Decimal]] = []
    for cid in all_cats:
        cur_amt = cur_by_cat.get(cid, Decimal("0"))
        prev_amt = prev_by_cat.get(cid, Decimal("0"))
        delta = cur_amt - prev_amt
        if abs(delta) >= MIN_ABS_DELTA:
            deltas.append((cid, cur_amt, prev_amt, delta))

    # Sắp theo |delta| giảm dần, lấy top.
    deltas.sort(key=lambda x: abs(x[3]), reverse=True)
    drivers: list[CategoryDriver] = []
    for cid, cur_amt, prev_amt, delta in deltas[:top_drivers]:
        if cid is None:
            cat_name = "Chưa phân loại"
        else:
            cat_name = name_map.get(cid, f"Category #{cid}")

        cat_delta_pct = (
            float(round((delta / prev_amt) * Decimal("100"), 2)) if prev_amt > 0 else None
        )

        # Drill-down merchant ở kỳ hiện tại + đối chiếu kỳ trước.
        cur_merchants = queries.query_merchant_aggregates_for_category(
            session, user_id, current, cid, limit=merchants_per_driver,
        )
        prev_merchants = queries.query_merchant_aggregates_for_category(
            session, user_id, previous, cid, limit=50,
        )
        prev_merchant_map = {m.merchant_name: m.total_amount for m in prev_merchants}
        contributions = [
            MerchantContribution(
                merchant_name=m.merchant_name,
                current_amount=m.total_amount,
                previous_amount=prev_merchant_map.get(m.merchant_name, Decimal("0")),
                delta_amount=m.total_amount - prev_merchant_map.get(m.merchant_name, Decimal("0")),
            )
            for m in cur_merchants
        ]

        drivers.append(
            CategoryDriver(
                category_id=cid,
                category_name=cat_name,
                current_amount=cur_amt,
                previous_amount=prev_amt,
                delta_amount=delta,
                delta_percent=cat_delta_pct,
                direction="increase" if delta > 0 else "decrease",
                top_merchants=contributions,
            ),
        )

    return SpendingDiagnostics(
        current_total=current_total,
        previous_total=previous_total,
        delta_amount=delta_total,
        delta_percent=delta_pct,
        drivers=drivers,
    )


__all__ = [
    "CategoryDriver",
    "MerchantContribution",
    "SpendingDiagnostics",
    "compute_spending_diagnostics",
]
