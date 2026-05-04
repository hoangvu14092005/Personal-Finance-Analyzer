"""Unit tests cho `app.services.budgets` (Phase 5.1 + 5.3).

Focus:
- `_parse_period_month` đúng với tháng 28/29/30/31 + invalid input.
- `compute_budget_usage` đúng status thresholds (safe/warning/exceeded).
- Sort order: percent_used desc.
- User isolation (chỉ trả budget của user hiện tại).
- `_compute_status` edge cases (boundary 80%, 100%).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from app.models.entities import Category, Transaction, User
from app.services.budgets import (
    WARNING_THRESHOLD,
    BudgetAlreadyExistsError,
    _compute_status,
    _parse_period_month,
    compute_budget_usage,
    create_budget,
    list_budgets_for_user,
)
from sqlalchemy.engine import Engine
from sqlmodel import Session


def _seed_user(session: Session, email: str = "budget@example.com") -> User:
    user = User(email=email, password_hash="hashed")
    session.add(user)
    session.commit()
    session.refresh(user)
    assert user.id is not None
    return user


def _seed_category(
    session: Session,
    name: str,
    color: str | None = "#f59e0b",
    user_id: int | None = None,
) -> Category:
    cat = Category(user_id=user_id, name=name, color=color, is_system=user_id is None)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    assert cat.id is not None
    return cat


class TestParsePeriodMonth:
    def test_january_has_31_days(self) -> None:
        start, end = _parse_period_month("2026-01")
        assert start == date(2026, 1, 1)
        assert end == date(2026, 1, 31)

    def test_february_leap_year(self) -> None:
        # 2024 là năm nhuận → 29 ngày.
        start, end = _parse_period_month("2024-02")
        assert end == date(2024, 2, 29)

    def test_february_non_leap_year(self) -> None:
        start, end = _parse_period_month("2026-02")
        assert end == date(2026, 2, 28)

    def test_april_has_30_days(self) -> None:
        _, end = _parse_period_month("2026-04")
        assert end == date(2026, 4, 30)

    def test_invalid_month_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_period_month("2026-13")

    def test_invalid_month_zero_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_period_month("2026-00")


class TestComputeStatus:
    def test_below_warning_is_safe(self) -> None:
        assert _compute_status(0.0) == "safe"
        assert _compute_status(79.99) == "safe"

    def test_boundary_warning(self) -> None:
        # Đúng 80% → warning (inclusive boundary).
        assert _compute_status(WARNING_THRESHOLD) == "warning"
        assert _compute_status(100.0) == "warning"

    def test_above_100_is_exceeded(self) -> None:
        assert _compute_status(100.01) == "exceeded"
        assert _compute_status(200.0) == "exceeded"


class TestCreateBudget:
    def test_happy_path(self, engine: Engine) -> None:
        with Session(engine) as session:
            user = _seed_user(session)
            cat = _seed_category(session, "Ăn uống")
            assert user.id is not None and cat.id is not None

            budget = create_budget(
                session=session,
                user_id=user.id,
                category_id=cat.id,
                period_month="2026-05",
                amount=Decimal("2000000"),
            )
            assert budget.id is not None
            assert budget.amount == Decimal("2000000")

    def test_duplicate_raises(self, engine: Engine) -> None:
        with Session(engine) as session:
            user = _seed_user(session)
            cat = _seed_category(session, "Ăn uống")
            assert user.id is not None and cat.id is not None

            create_budget(
                session=session,
                user_id=user.id,
                category_id=cat.id,
                period_month="2026-05",
                amount=Decimal("1000000"),
            )

            # Cùng user + category + period → duplicate.
            with pytest.raises(BudgetAlreadyExistsError):
                create_budget(
                    session=session,
                    user_id=user.id,
                    category_id=cat.id,
                    period_month="2026-05",
                    amount=Decimal("2000000"),
                )

    def test_same_category_different_month_ok(self, engine: Engine) -> None:
        with Session(engine) as session:
            user = _seed_user(session)
            cat = _seed_category(session, "Ăn uống")
            assert user.id is not None and cat.id is not None

            create_budget(
                session=session,
                user_id=user.id,
                category_id=cat.id,
                period_month="2026-05",
                amount=Decimal("1000000"),
            )
            # Tháng khác → OK.
            budget2 = create_budget(
                session=session,
                user_id=user.id,
                category_id=cat.id,
                period_month="2026-06",
                amount=Decimal("1500000"),
            )
            assert budget2.id is not None


class TestListBudgets:
    def test_user_isolation(self, engine: Engine) -> None:
        with Session(engine) as session:
            user1 = _seed_user(session, "u1@example.com")
            user2 = _seed_user(session, "u2@example.com")
            cat = _seed_category(session, "Ăn uống")
            assert user1.id is not None and user2.id is not None and cat.id is not None

            create_budget(
                session=session,
                user_id=user1.id,
                category_id=cat.id,
                period_month="2026-05",
                amount=Decimal("1000000"),
            )
            create_budget(
                session=session,
                user_id=user2.id,
                category_id=cat.id,
                period_month="2026-05",
                amount=Decimal("500000"),
            )

            rows1 = list_budgets_for_user(session, user1.id)
            rows2 = list_budgets_for_user(session, user2.id)
            assert len(rows1) == 1
            assert len(rows2) == 1
            assert rows1[0].user_id == user1.id
            assert rows1[0].amount == Decimal("1000000")


class TestComputeBudgetUsage:
    def _seed_scenario(self, session: Session) -> dict[str, int]:
        """Seed user + 2 categories + 2 budgets cho 2026-05 + transactions."""
        user = _seed_user(session)
        food = _seed_category(session, "Ăn uống", color="#f59e0b")
        transport = _seed_category(session, "Di chuyển", color="#3b82f6")
        assert user.id is not None and food.id is not None and transport.id is not None

        # Food budget: 1.000.000, sẽ spend 500.000 → 50% safe.
        food_budget = create_budget(
            session=session,
            user_id=user.id,
            category_id=food.id,
            period_month="2026-05",
            amount=Decimal("1000000"),
        )
        # Transport budget: 500.000, sẽ spend 600.000 → 120% exceeded.
        transport_budget = create_budget(
            session=session,
            user_id=user.id,
            category_id=transport.id,
            period_month="2026-05",
            amount=Decimal("500000"),
        )

        # Transactions: food = 300k + 200k = 500k trong May.
        session.add_all([
            Transaction(
                user_id=user.id,
                category_id=food.id,
                amount=Decimal("300000"),
                currency="VND",
                transaction_date=date(2026, 5, 1),
            ),
            Transaction(
                user_id=user.id,
                category_id=food.id,
                amount=Decimal("200000"),
                currency="VND",
                transaction_date=date(2026, 5, 20),
            ),
            # Transport = 600k.
            Transaction(
                user_id=user.id,
                category_id=transport.id,
                amount=Decimal("600000"),
                currency="VND",
                transaction_date=date(2026, 5, 10),
            ),
            # Transaction ngoài range (2026-04) không được tính.
            Transaction(
                user_id=user.id,
                category_id=food.id,
                amount=Decimal("999999"),
                currency="VND",
                transaction_date=date(2026, 4, 30),
            ),
        ])
        session.commit()

        return {
            "user_id": user.id,
            "food_id": food.id,
            "transport_id": transport.id,
            "food_budget_id": food_budget.id or 0,
            "transport_budget_id": transport_budget.id or 0,
        }

    def test_usage_computation_correct(self, engine: Engine) -> None:
        with Session(engine) as session:
            ids = self._seed_scenario(session)
            usages = compute_budget_usage(session, ids["user_id"], "2026-05")

        assert len(usages) == 2
        # Order: percent_used DESC → transport (120%) trước, food (50%) sau.
        assert usages[0].category_id == ids["transport_id"]
        assert usages[0].spent_amount == Decimal("600000")
        assert usages[0].remaining_amount == Decimal("-100000")
        assert usages[0].percent_used == 120.0
        assert usages[0].status == "exceeded"

        assert usages[1].category_id == ids["food_id"]
        assert usages[1].spent_amount == Decimal("500000")
        assert usages[1].percent_used == 50.0
        assert usages[1].status == "safe"

    def test_empty_when_no_budget(self, engine: Engine) -> None:
        with Session(engine) as session:
            user = _seed_user(session)
            assert user.id is not None
            usages = compute_budget_usage(session, user.id, "2026-05")
        assert usages == []

    def test_transactions_outside_period_not_counted(self, engine: Engine) -> None:
        """Cross-check: transactions tháng 4 không tính vào usage tháng 5."""
        with Session(engine) as session:
            user = _seed_user(session)
            cat = _seed_category(session, "Ăn uống")
            assert user.id is not None and cat.id is not None
            create_budget(
                session=session,
                user_id=user.id,
                category_id=cat.id,
                period_month="2026-05",
                amount=Decimal("1000000"),
            )
            # Transaction tháng 4 không tính.
            session.add(
                Transaction(
                    user_id=user.id,
                    category_id=cat.id,
                    amount=Decimal("999999"),
                    currency="VND",
                    transaction_date=date(2026, 4, 30),
                ),
            )
            # Transaction tháng 6 cũng không tính.
            session.add(
                Transaction(
                    user_id=user.id,
                    category_id=cat.id,
                    amount=Decimal("999999"),
                    currency="VND",
                    transaction_date=date(2026, 6, 1),
                ),
            )
            session.commit()

            usages = compute_budget_usage(session, user.id, "2026-05")
            assert len(usages) == 1
            assert usages[0].spent_amount == Decimal("0")
            assert usages[0].status == "safe"

    def test_warning_threshold_boundary(self, engine: Engine) -> None:
        """Spent = 80% of budget → status = warning."""
        with Session(engine) as session:
            user = _seed_user(session)
            cat = _seed_category(session, "Ăn uống")
            assert user.id is not None and cat.id is not None
            create_budget(
                session=session,
                user_id=user.id,
                category_id=cat.id,
                period_month="2026-05",
                amount=Decimal("1000000"),
            )
            session.add(
                Transaction(
                    user_id=user.id,
                    category_id=cat.id,
                    amount=Decimal("800000"),  # Đúng 80%.
                    currency="VND",
                    transaction_date=date(2026, 5, 15),
                ),
            )
            session.commit()

            usages = compute_budget_usage(session, user.id, "2026-05")
            assert usages[0].percent_used == 80.0
            assert usages[0].status == "warning"
