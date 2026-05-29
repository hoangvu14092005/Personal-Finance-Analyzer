"""Analytics service cho dashboard summary (Phase 4.2).

Tổng hợp dữ liệu chi tiêu theo `DateRange`:
- total_spend: tổng amount
- transaction_count: số giao dịch
- top_categories: top N category theo chi tiêu (có name, color, amount, count, percentage)
- recent_transactions: N giao dịch gần nhất trong range
- previous_period: tổng + delta cho cùng range trước đó

Tất cả đều scope theo `user_id` để đảm bảo isolation. Query đi qua SQLModel
session — engine từ caller (FastAPI dependency).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.engine import Row
from sqlmodel import Session, col, func, select

from app.models.entities import Category, Transaction
from app.services.date_ranges import DateRange

# Top N category cho dashboard. UI sẽ render thêm nhóm "Khác" nếu cần.
DEFAULT_TOP_CATEGORIES_LIMIT = 5
# Recent transaction list trên dashboard (UI hiển thị mini list, link đến /transactions).
DEFAULT_RECENT_TRANSACTIONS_LIMIT = 5


@dataclass(frozen=True, slots=True)
class CategoryBreakdown:
    """Một dòng trong top categories."""

    category_id: int | None  # None = giao dịch không gán category.
    name: str
    color: str | None
    total_amount: Decimal
    transaction_count: int
    percentage: float  # 0..100, làm tròn 2 chữ số (caller có thể format).


@dataclass(frozen=True, slots=True)
class RecentTransactionItem:
    """Phiên bản gọn của Transaction cho dashboard."""

    id: int
    merchant_name: str | None
    amount: Decimal
    currency: str
    transaction_date: str  # ISO format YYYY-MM-DD
    category_id: int | None
    category_name: str | None


@dataclass(frozen=True, slots=True)
class MerchantBreakdown:
    """Một dòng merchant aggregation."""

    merchant_name: str
    total_amount: Decimal
    transaction_count: int
    percentage: float


@dataclass(frozen=True, slots=True)
class TrendPoint:
    period_start: date
    period_end: date
    amount: Decimal
    transaction_count: int


@dataclass(frozen=True, slots=True)
class CalendarDay:
    date: date
    amount: Decimal
    transaction_count: int
    intensity: int
    top_category_name: str | None
    is_unusual: bool


@dataclass(frozen=True, slots=True)
class SpendingAnomaly:
    id: str
    type: str
    severity: str
    title: str
    transaction_id: int
    merchant_name: str | None
    transaction_date: date
    amount: Decimal
    baseline_amount: Decimal
    reason: str


@dataclass(frozen=True, slots=True)
class PeriodTotals:
    """Tổng cho một period (current hoặc previous)."""

    total_spend: Decimal
    transaction_count: int


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    """Payload tổng cho dashboard summary endpoint."""

    current: PeriodTotals
    previous: PeriodTotals
    delta_amount: Decimal  # current.total_spend - previous.total_spend
    delta_percent: float | None  # None nếu previous = 0 (tránh chia 0).
    top_categories: list[CategoryBreakdown]
    recent_transactions: list[RecentTransactionItem]


def _query_period_totals(
    session: Session,
    user_id: int,
    range_: DateRange,
) -> PeriodTotals:
    """SUM(amount) + COUNT(*) cho range."""
    statement = (
        select(
            func.coalesce(func.sum(Transaction.amount), 0),
            func.count(Transaction.id),
        )
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
    )
    row = session.exec(statement).one()
    total_raw, count_raw = row
    # SQLite trả 0 (int) khi không có row; cast về Decimal để consistent.
    total = Decimal(str(total_raw)) if total_raw is not None else Decimal("0")
    return PeriodTotals(total_spend=total, transaction_count=int(count_raw or 0))


def _query_top_categories(
    session: Session,
    user_id: int,
    range_: DateRange,
    total_spend: Decimal,
    limit: int = DEFAULT_TOP_CATEGORIES_LIMIT,
) -> list[CategoryBreakdown]:
    """GROUP BY category, ORDER BY SUM DESC, LIMIT N.

    Giao dịch không có category (`category_id IS NULL`) được gộp vào nhóm
    "Chưa phân loại" để UI vẫn hiển thị.
    """
    total_expr = func.coalesce(func.sum(Transaction.amount), 0).label("total")
    statement = (
        select(
            Transaction.category_id,
            total_expr,
            func.count(Transaction.id).label("cnt"),
        )
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
        .group_by(col(Transaction.category_id))
        .order_by(total_expr.desc())
        .limit(limit)
    )
    rows = session.exec(statement).all()
    if not rows:
        return []

    # Lấy categories trong 1 query để có name + color.
    category_ids = [row[0] for row in rows if row[0] is not None]
    category_map: dict[int, Category] = {}
    if category_ids:
        cat_statement = select(Category).where(col(Category.id).in_(category_ids))
        for cat in session.exec(cat_statement).all():
            if cat.id is not None:
                category_map[cat.id] = cat

    breakdowns: list[CategoryBreakdown] = []
    for row in rows:
        category_id = row[0]
        amount = Decimal(str(row[1])) if row[1] is not None else Decimal("0")
        count = int(row[2] or 0)

        if category_id is None:
            name = "Chưa phân loại"
            color = None
        else:
            cat = category_map.get(category_id)
            name = cat.name if cat is not None else f"Category #{category_id}"
            color = cat.color if cat is not None else None

        # Percentage: tỉ lệ amount / total_spend × 100. total_spend đã từ
        # PeriodTotals nên consistent (không bị off-by-one giữa 2 query).
        if total_spend > 0:
            pct_raw = (amount / total_spend) * Decimal("100")
            percentage = float(round(pct_raw, 2))
        else:
            percentage = 0.0

        breakdowns.append(
            CategoryBreakdown(
                category_id=category_id,
                name=name,
                color=color,
                total_amount=amount,
                transaction_count=count,
                percentage=percentage,
            ),
        )
    return breakdowns


def _query_recent_transactions(
    session: Session,
    user_id: int,
    range_: DateRange,
    limit: int = DEFAULT_RECENT_TRANSACTIONS_LIMIT,
) -> list[RecentTransactionItem]:
    """N transaction mới nhất trong range, kèm category name (LEFT JOIN).

    Order: `transaction_date DESC, id DESC` để 2 transaction cùng ngày vẫn
    deterministic (id mới hơn lên trước).
    """
    statement = (
        select(Transaction, Category)
        .join(Category, col(Transaction.category_id) == Category.id, isouter=True)
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
        .order_by(col(Transaction.transaction_date).desc(), col(Transaction.id).desc())
        .limit(limit)
    )
    items: list[RecentTransactionItem] = []
    rows: list[Row[tuple[Transaction, Category | None]]] = list(
        session.exec(statement).all(),  # type: ignore[arg-type]
    )
    for row in rows:
        transaction, category = row
        if transaction.id is None:
            continue  # Pragmatic guard — DB sẽ luôn có id sau commit.
        items.append(
            RecentTransactionItem(
                id=transaction.id,
                merchant_name=transaction.merchant_name,
                amount=transaction.amount,
                currency=transaction.currency,
                transaction_date=transaction.transaction_date.isoformat(),
                category_id=transaction.category_id,
                category_name=category.name if category is not None else None,
            ),
        )
    return items


def compute_summary(
    session: Session,
    user_id: int,
    current: DateRange,
    previous: DateRange,
    *,
    top_categories_limit: int = DEFAULT_TOP_CATEGORIES_LIMIT,
    recent_transactions_limit: int = DEFAULT_RECENT_TRANSACTIONS_LIMIT,
) -> DashboardSummary:
    """Tính toán toàn bộ dashboard summary cho 1 user trong 1 range.

    Thực hiện 4 queries (1 trip / metric):
    1. SUM + COUNT cho `current`.
    2. SUM + COUNT cho `previous`.
    3. GROUP BY category cho `current` (top N).
    4. SELECT recent transactions với JOIN Category.

    Dataset MVP nhỏ (<10k rows / user) nên không cần optimize hơn. Khi cần
    có thể gộp #1 + #3 dùng Window function, hoặc cache layer.
    """
    current_totals = _query_period_totals(session, user_id, current)
    previous_totals = _query_period_totals(session, user_id, previous)

    delta_amount = current_totals.total_spend - previous_totals.total_spend
    if previous_totals.total_spend > 0:
        delta_pct_raw = (delta_amount / previous_totals.total_spend) * Decimal("100")
        delta_percent: float | None = float(round(delta_pct_raw, 2))
    else:
        # Không có spending kỳ trước → không tính được %; UI sẽ render "—".
        delta_percent = None

    top_categories = _query_top_categories(
        session,
        user_id,
        current,
        current_totals.total_spend,
        limit=top_categories_limit,
    )
    recent_transactions = _query_recent_transactions(
        session,
        user_id,
        current,
        limit=recent_transactions_limit,
    )

    return DashboardSummary(
        current=current_totals,
        previous=previous_totals,
        delta_amount=delta_amount,
        delta_percent=delta_percent,
        top_categories=top_categories,
        recent_transactions=recent_transactions,
    )


def compute_category_breakdown(
    session: Session,
    user_id: int,
    range_: DateRange,
    *,
    limit: int = DEFAULT_TOP_CATEGORIES_LIMIT,
) -> list[CategoryBreakdown]:
    """Public wrapper cho `/analytics/categories`."""
    totals = _query_period_totals(session, user_id, range_)
    return _query_top_categories(
        session,
        user_id,
        range_,
        totals.total_spend,
        limit=limit,
    )


def compute_merchant_breakdown(
    session: Session,
    user_id: int,
    range_: DateRange,
    *,
    limit: int = 10,
) -> list[MerchantBreakdown]:
    """Top merchants theo tổng chi trong range.

    Chỉ đọc `transactions`, đúng source-of-truth cho analytics tiền.
    Transaction không có merchant_name được gom vào "Không rõ".
    """
    totals = _query_period_totals(session, user_id, range_)
    total_spend = totals.total_spend

    merchant_expr = func.coalesce(Transaction.merchant_name, "Không rõ").label("merchant")
    total_expr = func.coalesce(func.sum(Transaction.amount), 0).label("total")
    statement = (
        select(
            merchant_expr,
            total_expr,
            func.count(Transaction.id).label("cnt"),
        )
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
        .group_by(merchant_expr)
        .order_by(total_expr.desc())
        .limit(limit)
    )

    rows = session.exec(statement).all()
    items: list[MerchantBreakdown] = []
    for row in rows:
        merchant_name = str(row[0] or "Không rõ")
        amount = Decimal(str(row[1])) if row[1] is not None else Decimal("0")
        count = int(row[2] or 0)
        if total_spend > 0:
            percentage = float(round((amount / total_spend) * Decimal("100"), 2))
        else:
            percentage = 0.0
        items.append(
            MerchantBreakdown(
                merchant_name=merchant_name,
                total_amount=amount,
                transaction_count=count,
                percentage=percentage,
            ),
        )
    return items


def _query_transactions_for_range(
    session: Session,
    user_id: int,
    range_: DateRange,
) -> list[Transaction]:
    statement = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
        .order_by(col(Transaction.transaction_date).asc(), col(Transaction.id).asc())
    )
    return list(session.exec(statement).all())


def _period_key(value: date, group_by: str) -> tuple[date, date]:
    if group_by == "week":
        start = value - timedelta(days=value.weekday())
        return start, start + timedelta(days=6)
    if group_by == "month":
        start = value.replace(day=1)
        if start.month == 12:
            next_month = date(start.year + 1, 1, 1)
        else:
            next_month = date(start.year, start.month + 1, 1)
        return start, next_month - timedelta(days=1)
    return value, value


def compute_spending_trends(
    session: Session,
    user_id: int,
    range_: DateRange,
    *,
    group_by: str = "day",
) -> list[TrendPoint]:
    """Return spending series from confirmed transactions only."""
    transactions = _query_transactions_for_range(session, user_id, range_)
    grouped: dict[tuple[date, date], tuple[Decimal, int]] = defaultdict(lambda: (Decimal("0"), 0))
    for transaction in transactions:
        key = _period_key(transaction.transaction_date, group_by)
        total, count = grouped[key]
        grouped[key] = (total + transaction.amount, count + 1)

    points: list[TrendPoint] = []
    if group_by == "day":
        current = range_.start
        while current <= range_.end:
            total, count = grouped.get((current, current), (Decimal("0"), 0))
            points.append(
                TrendPoint(
                    period_start=current,
                    period_end=current,
                    amount=total,
                    transaction_count=count,
                ),
            )
            current += timedelta(days=1)
        return points

    for (period_start, period_end), (amount, count) in sorted(grouped.items()):
        points.append(
            TrendPoint(
                period_start=max(period_start, range_.start),
                period_end=min(period_end, range_.end),
                amount=amount,
                transaction_count=count,
            ),
        )
    return points


def _category_name_map(session: Session, category_ids: set[int]) -> dict[int, str]:
    if not category_ids:
        return {}
    rows = session.exec(select(Category).where(col(Category.id).in_(category_ids))).all()
    return {category.id: category.name for category in rows if category.id is not None}


def compute_calendar_days(
    session: Session,
    user_id: int,
    range_: DateRange,
) -> list[CalendarDay]:
    transactions = _query_transactions_for_range(session, user_id, range_)
    totals_by_day: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    counts_by_day: dict[date, int] = defaultdict(int)
    category_totals_by_day: dict[date, dict[int, Decimal]] = defaultdict(
        lambda: defaultdict(lambda: Decimal("0")),
    )

    category_ids: set[int] = set()
    for transaction in transactions:
        day = transaction.transaction_date
        totals_by_day[day] += transaction.amount
        counts_by_day[day] += 1
        if transaction.category_id is not None:
            category_ids.add(transaction.category_id)
            category_totals_by_day[day][transaction.category_id] += transaction.amount

    non_zero_totals = [amount for amount in totals_by_day.values() if amount > 0]
    max_total = max(non_zero_totals, default=Decimal("0"))
    avg_total = (
        sum(non_zero_totals, Decimal("0")) / len(non_zero_totals)
        if non_zero_totals
        else Decimal("0")
    )
    category_names = _category_name_map(session, category_ids)

    days: list[CalendarDay] = []
    current = range_.start
    while current <= range_.end:
        amount = totals_by_day.get(current, Decimal("0"))
        count = counts_by_day.get(current, 0)
        if amount <= 0 or max_total <= 0:
            intensity = 0
        else:
            intensity = min(4, max(1, int((amount / max_total) * Decimal("4"))))
        is_unusual = bool(amount > 0 and avg_total > 0 and amount >= avg_total * Decimal("2"))
        if is_unusual:
            intensity = 4

        top_category_name = None
        day_category_totals = category_totals_by_day.get(current, {})
        if day_category_totals:
            top_category_id = max(day_category_totals.items(), key=lambda item: item[1])[0]
            top_category_name = category_names.get(top_category_id)

        days.append(
            CalendarDay(
                date=current,
                amount=amount,
                transaction_count=count,
                intensity=intensity,
                top_category_name=top_category_name,
                is_unusual=is_unusual,
            ),
        )
        current += timedelta(days=1)
    return days


def compute_spending_anomalies(
    session: Session,
    user_id: int,
    range_: DateRange,
    *,
    limit: int = 10,
) -> list[SpendingAnomaly]:
    transactions = _query_transactions_for_range(session, user_id, range_)
    if len(transactions) < 3:
        return []

    total = sum((transaction.amount for transaction in transactions), Decimal("0"))
    baseline = total / len(transactions)
    threshold = baseline * Decimal("2")
    anomalies: list[SpendingAnomaly] = []
    for transaction in sorted(transactions, key=lambda tx: tx.amount, reverse=True):
        if transaction.id is None or transaction.amount < threshold:
            continue
        over_percent = ((transaction.amount - baseline) / baseline) * Decimal("100")
        severity = "danger" if transaction.amount >= baseline * Decimal("3") else "warning"
        anomalies.append(
            SpendingAnomaly(
                id=f"tx_{transaction.id}_large",
                type="large_transaction",
                severity=severity,
                title="Giao dịch lớn bất thường",
                transaction_id=transaction.id,
                merchant_name=transaction.merchant_name,
                transaction_date=transaction.transaction_date,
                amount=transaction.amount,
                baseline_amount=baseline,
                reason=f"Cao hơn trung bình {round(over_percent, 2)}% trong kỳ.",
            ),
        )
        if len(anomalies) >= limit:
            break
    return anomalies


__all__ = [
    "DEFAULT_RECENT_TRANSACTIONS_LIMIT",
    "DEFAULT_TOP_CATEGORIES_LIMIT",
    "CategoryBreakdown",
    "DashboardSummary",
    "CalendarDay",
    "MerchantBreakdown",
    "PeriodTotals",
    "RecentTransactionItem",
    "SpendingAnomaly",
    "TrendPoint",
    "compute_category_breakdown",
    "compute_calendar_days",
    "compute_merchant_breakdown",
    "compute_spending_anomalies",
    "compute_spending_trends",
    "compute_summary",
]
