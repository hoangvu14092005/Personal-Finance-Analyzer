"""Budget service (Phase 5): CRUD + usage calculation.

Domain:
- Một user có nhiều budgets, mỗi budget gắn với 1 `category` và 1 `period_month`
  (YYYY-MM). UniqueConstraint (user_id, category_id, period_month) ở DB đảm
  bảo không có duplicate.
- Usage = `SUM(transactions.amount)` cho category đó trong khoảng ngày của
  `period_month` (first_day..last_day) của user.
- Status:
  - `safe`     : percent < WARNING_THRESHOLD (80%)
  - `warning`  : WARNING_THRESHOLD <= percent <= 100 (sắp vượt)
  - `exceeded` : percent > 100 (đã vượt)

Ghi chú:
- Percent là `float` đã round 2 chữ số — dùng cho UI, không dùng làm logic.
- `BudgetAlreadyExistsError` raise khi cố tạo budget trùng (user, category, month).
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, func, select

from app.models.entities import Budget, Category, Transaction

WARNING_THRESHOLD = 80.0  # %


class BudgetAlreadyExistsError(Exception):
    """User đã có budget cho (category, period_month) này."""


class BudgetNotFoundError(Exception):
    """Budget không tồn tại hoặc không thuộc user."""


@dataclass(frozen=True, slots=True)
class BudgetUsage:
    """Kết quả usage cho 1 budget."""

    budget_id: int
    category_id: int
    category_name: str
    category_color: str | None
    period_month: str
    budget_amount: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    percent_used: float  # 0..inf (không clamp 100 để UI render "120%").
    status: str  # "safe" | "warning" | "exceeded"


def _parse_period_month(period_month: str) -> tuple[date, date]:
    """Parse "YYYY-MM" → (first_day, last_day).

    Dùng `calendar.monthrange` để handle đúng tháng 28/29/30/31. Raise
    `ValueError` nếu format sai (caller nên validate từ Pydantic).
    """
    year_str, month_str = period_month.split("-", 1)
    year = int(year_str)
    month = int(month_str)
    if not (1 <= month <= 12):
        raise ValueError(f"Invalid month in period_month: {period_month}")
    _, last_day = calendar.monthrange(year, month)
    return date(year, month, 1), date(year, month, last_day)


def _compute_status(percent_used: float) -> str:
    if percent_used > 100.0:
        return "exceeded"
    if percent_used >= WARNING_THRESHOLD:
        return "warning"
    return "safe"


def create_budget(
    session: Session,
    user_id: int,
    category_id: int,
    period_month: str,
    amount: Decimal,
) -> Budget:
    """Create mới. Raise `BudgetAlreadyExistsError` nếu unique constraint fail."""
    budget = Budget(
        user_id=user_id,
        category_id=category_id,
        period_month=period_month,
        amount=amount,
    )
    session.add(budget)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise BudgetAlreadyExistsError(
            f"Budget cho category {category_id} tháng {period_month} đã tồn tại",
        ) from exc
    session.refresh(budget)
    return budget


def get_budget_for_user(
    session: Session,
    budget_id: int,
    user_id: int,
) -> Budget:
    """Get + enforce ownership. Raise `BudgetNotFoundError` nếu không thấy hoặc
    thuộc user khác."""
    budget = session.get(Budget, budget_id)
    if budget is None or budget.user_id != user_id:
        raise BudgetNotFoundError(f"Budget {budget_id} not found")
    return budget


def list_budgets_for_user(
    session: Session,
    user_id: int,
    period_month: str | None = None,
) -> list[Budget]:
    """List budgets của user. Optional filter theo `period_month`.

    Order: period_month DESC, category_id ASC (các budget gần nhất đầu tiên).
    """
    statement = select(Budget).where(Budget.user_id == user_id)
    if period_month is not None:
        statement = statement.where(Budget.period_month == period_month)
    statement = statement.order_by(
        col(Budget.period_month).desc(),
        col(Budget.category_id).asc(),
    )
    return list(session.exec(statement).all())


def update_budget_amount(
    session: Session,
    budget: Budget,
    new_amount: Decimal,
) -> Budget:
    """Đổi `amount`. Không cho đổi category_id / period_month (UX: delete + create)."""
    budget.amount = new_amount
    session.add(budget)
    session.commit()
    session.refresh(budget)
    return budget


def delete_budget(session: Session, budget: Budget) -> None:
    session.delete(budget)
    session.commit()


def compute_budget_usage(
    session: Session,
    user_id: int,
    period_month: str,
) -> list[BudgetUsage]:
    """Tính usage cho tất cả budget của user trong `period_month`.

    Strategy:
    1. Lấy toàn bộ budgets cho (user, period) — 1 query.
    2. Lấy category metadata (name, color) — 1 query theo IN (category_ids).
    3. Aggregate SUM(amount) per category trong khoảng ngày — 1 query GROUP BY.
    4. Merge 3 phần → list[BudgetUsage], ordered by percent_used DESC.

    Order: theo % used giảm dần → UI highlight category vượt/sắp vượt ngay đầu.
    """
    budgets = list_budgets_for_user(session, user_id, period_month=period_month)
    if not budgets:
        return []

    start_date, end_date = _parse_period_month(period_month)
    category_ids = [b.category_id for b in budgets]

    # Categories: name + color.
    cat_statement = select(Category).where(col(Category.id).in_(category_ids))
    category_map: dict[int, Category] = {}
    for cat in session.exec(cat_statement).all():
        if cat.id is not None:
            category_map[cat.id] = cat

    # Aggregate spend per category trong khoảng ngày.
    spend_statement = (
        select(
            Transaction.category_id,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= start_date)
        .where(Transaction.transaction_date <= end_date)
        .where(col(Transaction.category_id).in_(category_ids))
        .group_by(col(Transaction.category_id))
    )
    spend_map: dict[int, Decimal] = {}
    for row in session.exec(spend_statement).all():
        cat_id, total = row[0], row[1]
        if cat_id is not None:
            spend_map[cat_id] = Decimal(str(total)) if total is not None else Decimal("0")

    usages: list[BudgetUsage] = []
    for budget in budgets:
        if budget.id is None:
            continue  # Pragmatic guard.
        spent = spend_map.get(budget.category_id, Decimal("0"))
        remaining = budget.amount - spent
        # Percent dùng float để phù hợp với status ranges. Budget luôn > 0 theo
        # validator nên không cần guard chia 0.
        percent_raw = (spent / budget.amount) * Decimal("100")
        percent = float(round(percent_raw, 2))

        cat = category_map.get(budget.category_id)
        cat_name = cat.name if cat is not None else f"Category #{budget.category_id}"
        cat_color = cat.color if cat is not None else None

        usages.append(
            BudgetUsage(
                budget_id=budget.id,
                category_id=budget.category_id,
                category_name=cat_name,
                category_color=cat_color,
                period_month=budget.period_month,
                budget_amount=budget.amount,
                spent_amount=spent,
                remaining_amount=remaining,
                percent_used=percent,
                status=_compute_status(percent),
            ),
        )

    # Sort theo % used DESC để UI highlight category over-budget đầu tiên.
    usages.sort(key=lambda u: u.percent_used, reverse=True)
    return usages


__all__ = [
    "WARNING_THRESHOLD",
    "BudgetAlreadyExistsError",
    "BudgetNotFoundError",
    "BudgetUsage",
    "compute_budget_usage",
    "create_budget",
    "delete_budget",
    "get_budget_for_user",
    "list_budgets_for_user",
    "update_budget_amount",
]
