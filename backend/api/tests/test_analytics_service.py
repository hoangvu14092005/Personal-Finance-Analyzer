"""Tests cho `app.services.analytics.compute_summary` (Phase 4.2).

Sử dụng SQLite in-memory + fixtures conftest. Test với fixture dataset cố
định để verify aggregation đúng.
"""
from __future__ import annotations

from collections.abc import Generator
from datetime import date
from decimal import Decimal

import pytest
from app.models.entities import Category, Transaction, User
from app.services.analytics import (
    DEFAULT_TOP_CATEGORIES_LIMIT,
    compute_summary,
)
from app.services.date_ranges import DateRange
from sqlmodel import Session


@pytest.fixture
def seed_user(db_session: Session) -> User:
    user = User(email="dash@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def seed_categories(db_session: Session) -> dict[str, Category]:
    food = Category(user_id=None, name="Ăn uống", is_system=True, color="#f59e0b")
    transport = Category(user_id=None, name="Di chuyển", is_system=True, color="#3b82f6")
    shopping = Category(user_id=None, name="Mua sắm", is_system=True, color="#ef4444")
    db_session.add_all([food, transport, shopping])
    db_session.commit()
    db_session.refresh(food)
    db_session.refresh(transport)
    db_session.refresh(shopping)
    return {"food": food, "transport": transport, "shopping": shopping}


@pytest.fixture
def seed_transactions(
    db_session: Session,
    seed_user: User,
    seed_categories: dict[str, Category],
) -> Generator[None, None, None]:
    """Dataset:

    Current period (2026-04-01 ~ 2026-04-15):
    - 2x Ăn uống: 100k + 50k = 150k
    - 1x Di chuyển: 30k
    - 1x Mua sắm: 200k
    - 1x null category: 20k
    => total = 400k, count = 5

    Previous period (2026-03-17 ~ 2026-03-31):
    - 2x Ăn uống: 80k + 60k = 140k
    - 1x Di chuyển: 25k
    => total = 165k, count = 3

    Out-of-range (2026-02-15) — không được tính:
    - 1x: 999k
    """
    assert seed_user.id is not None
    user_id = seed_user.id
    cats = seed_categories

    rows = [
        # Current period.
        Transaction(
            user_id=user_id,
            category_id=cats["food"].id,
            merchant_name="Cafe A",
            amount=Decimal("100000"),
            currency="VND",
            transaction_date=date(2026, 4, 10),
        ),
        Transaction(
            user_id=user_id,
            category_id=cats["food"].id,
            merchant_name="Cafe B",
            amount=Decimal("50000"),
            currency="VND",
            transaction_date=date(2026, 4, 12),
        ),
        Transaction(
            user_id=user_id,
            category_id=cats["transport"].id,
            merchant_name="Grab",
            amount=Decimal("30000"),
            currency="VND",
            transaction_date=date(2026, 4, 5),
        ),
        Transaction(
            user_id=user_id,
            category_id=cats["shopping"].id,
            merchant_name="Mall",
            amount=Decimal("200000"),
            currency="VND",
            transaction_date=date(2026, 4, 14),
        ),
        Transaction(
            user_id=user_id,
            category_id=None,
            merchant_name="Misc",
            amount=Decimal("20000"),
            currency="VND",
            transaction_date=date(2026, 4, 8),
        ),
        # Previous period.
        Transaction(
            user_id=user_id,
            category_id=cats["food"].id,
            merchant_name="Cafe C",
            amount=Decimal("80000"),
            currency="VND",
            transaction_date=date(2026, 3, 25),
        ),
        Transaction(
            user_id=user_id,
            category_id=cats["food"].id,
            merchant_name="Cafe D",
            amount=Decimal("60000"),
            currency="VND",
            transaction_date=date(2026, 3, 28),
        ),
        Transaction(
            user_id=user_id,
            category_id=cats["transport"].id,
            merchant_name="Bus",
            amount=Decimal("25000"),
            currency="VND",
            transaction_date=date(2026, 3, 20),
        ),
        # Out-of-range.
        Transaction(
            user_id=user_id,
            category_id=cats["shopping"].id,
            merchant_name="Old",
            amount=Decimal("999000"),
            currency="VND",
            transaction_date=date(2026, 2, 15),
        ),
    ]
    db_session.add_all(rows)
    db_session.commit()
    yield


CURRENT_RANGE = DateRange(start=date(2026, 4, 1), end=date(2026, 4, 15))
PREVIOUS_RANGE = DateRange(start=date(2026, 3, 17), end=date(2026, 3, 31))


class TestComputeSummary:
    def test_totals_match_seed_data(
        self,
        db_session: Session,
        seed_user: User,
        seed_transactions: None,  # noqa: ARG002
    ) -> None:
        assert seed_user.id is not None
        result = compute_summary(
            db_session,
            seed_user.id,
            CURRENT_RANGE,
            PREVIOUS_RANGE,
        )
        assert result.current.total_spend == Decimal("400000")
        assert result.current.transaction_count == 5
        assert result.previous.total_spend == Decimal("165000")
        assert result.previous.transaction_count == 3

    def test_delta_amount_and_percent(
        self,
        db_session: Session,
        seed_user: User,
        seed_transactions: None,  # noqa: ARG002
    ) -> None:
        assert seed_user.id is not None
        result = compute_summary(
            db_session,
            seed_user.id,
            CURRENT_RANGE,
            PREVIOUS_RANGE,
        )
        # 400k - 165k = 235k.
        assert result.delta_amount == Decimal("235000")
        # 235k / 165k * 100 ≈ 142.42%.
        assert result.delta_percent is not None
        assert abs(result.delta_percent - 142.42) < 0.05

    def test_delta_percent_none_when_previous_zero(
        self,
        db_session: Session,
        seed_user: User,
    ) -> None:
        # Không seed transactions nào → previous=0 và current=0 đều là 0.
        # Add 1 transaction current period chỉ để current > 0.
        assert seed_user.id is not None
        db_session.add(
            Transaction(
                user_id=seed_user.id,
                category_id=None,
                amount=Decimal("100000"),
                currency="VND",
                transaction_date=date(2026, 4, 10),
            ),
        )
        db_session.commit()

        result = compute_summary(
            db_session,
            seed_user.id,
            CURRENT_RANGE,
            PREVIOUS_RANGE,
        )
        assert result.previous.total_spend == Decimal("0")
        assert result.delta_percent is None  # Không chia 0.

    def test_top_categories_ordered_by_amount(
        self,
        db_session: Session,
        seed_user: User,
        seed_categories: dict[str, Category],
        seed_transactions: None,  # noqa: ARG002
    ) -> None:
        assert seed_user.id is not None
        result = compute_summary(
            db_session,
            seed_user.id,
            CURRENT_RANGE,
            PREVIOUS_RANGE,
        )

        # 4 nhóm: Mua sắm (200k), Ăn uống (150k), Di chuyển (30k), null (20k).
        # DEFAULT_TOP = 5 nên trả tất cả.
        assert len(result.top_categories) == 4
        names = [c.name for c in result.top_categories]
        assert names == ["Mua sắm", "Ăn uống", "Di chuyển", "Chưa phân loại"]

        # Verify amounts.
        assert result.top_categories[0].total_amount == Decimal("200000")
        assert result.top_categories[1].total_amount == Decimal("150000")

        # Percentage: 200000 / 400000 = 50.0%.
        assert abs(result.top_categories[0].percentage - 50.0) < 0.01
        # 150000 / 400000 = 37.5%.
        assert abs(result.top_categories[1].percentage - 37.5) < 0.01

        # Color preserved cho category có color.
        assert result.top_categories[0].color == seed_categories["shopping"].color

    def test_top_categories_respects_limit(
        self,
        db_session: Session,
        seed_user: User,
        seed_transactions: None,  # noqa: ARG002
    ) -> None:
        assert seed_user.id is not None
        result = compute_summary(
            db_session,
            seed_user.id,
            CURRENT_RANGE,
            PREVIOUS_RANGE,
            top_categories_limit=2,
        )
        assert len(result.top_categories) == 2
        # Top 2: Mua sắm (200k), Ăn uống (150k).
        assert result.top_categories[0].name == "Mua sắm"
        assert result.top_categories[1].name == "Ăn uống"

    def test_recent_transactions_ordered_by_date_desc(
        self,
        db_session: Session,
        seed_user: User,
        seed_transactions: None,  # noqa: ARG002
    ) -> None:
        assert seed_user.id is not None
        result = compute_summary(
            db_session,
            seed_user.id,
            CURRENT_RANGE,
            PREVIOUS_RANGE,
            recent_transactions_limit=10,
        )
        # 5 transactions trong current range, order by date desc.
        assert len(result.recent_transactions) == 5
        dates = [t.transaction_date for t in result.recent_transactions]
        assert dates == sorted(dates, reverse=True)
        # Đầu tiên: Mall 2026-04-14.
        first = result.recent_transactions[0]
        assert first.merchant_name == "Mall"
        assert first.transaction_date == "2026-04-14"
        assert first.category_name == "Mua sắm"

    def test_recent_transactions_respects_limit(
        self,
        db_session: Session,
        seed_user: User,
        seed_transactions: None,  # noqa: ARG002
    ) -> None:
        assert seed_user.id is not None
        result = compute_summary(
            db_session,
            seed_user.id,
            CURRENT_RANGE,
            PREVIOUS_RANGE,
            recent_transactions_limit=3,
        )
        assert len(result.recent_transactions) == 3

    def test_user_isolation(
        self,
        db_session: Session,
        seed_user: User,
        seed_categories: dict[str, Category],
        seed_transactions: None,  # noqa: ARG002
    ) -> None:
        # Tạo user khác với 1 transaction trong current range.
        other = User(email="other@example.com", password_hash="x")
        db_session.add(other)
        db_session.commit()
        db_session.refresh(other)
        assert other.id is not None

        db_session.add(
            Transaction(
                user_id=other.id,
                category_id=seed_categories["food"].id,
                amount=Decimal("999999"),
                currency="VND",
                transaction_date=date(2026, 4, 10),
            ),
        )
        db_session.commit()

        # User gốc không thấy transaction của user khác.
        assert seed_user.id is not None
        result = compute_summary(
            db_session,
            seed_user.id,
            CURRENT_RANGE,
            PREVIOUS_RANGE,
        )
        assert result.current.total_spend == Decimal("400000")  # Không bao gồm 999999.

    def test_empty_dataset_returns_zeros(
        self,
        db_session: Session,
        seed_user: User,
    ) -> None:
        assert seed_user.id is not None
        result = compute_summary(
            db_session,
            seed_user.id,
            CURRENT_RANGE,
            PREVIOUS_RANGE,
        )
        assert result.current.total_spend == Decimal("0")
        assert result.current.transaction_count == 0
        assert result.previous.total_spend == Decimal("0")
        assert result.delta_amount == Decimal("0")
        assert result.delta_percent is None
        assert result.top_categories == []
        assert result.recent_transactions == []

    def test_default_top_categories_limit_is_five(self) -> None:
        # Sanity check constant — đảm bảo schema/UI đồng bộ.
        assert DEFAULT_TOP_CATEGORIES_LIMIT == 5
