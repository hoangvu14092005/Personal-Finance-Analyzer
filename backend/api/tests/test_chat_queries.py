"""Tests cho chat query service layer (Phase 6.1).

Verify:
- Mỗi function trả đúng format.
- User isolation: user A không thấy data user B.
- Empty data trả empty collection, không raise.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from app.models.entities import Category, Transaction, User
from app.services.chat.queries import (
    compare_periods,
    get_budget_status,
    get_recent_transactions,
    get_spending_by_day,
    get_top_merchants,
    query_spending_summary,
    search_transactions,
)
from sqlmodel import Session


@pytest.fixture()
def user_a(db_session: Session) -> int:
    user = User(email="a@test.com", password_hash="x", full_name="User A")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    assert user.id is not None
    return user.id


@pytest.fixture()
def user_b(db_session: Session) -> int:
    user = User(email="b@test.com", password_hash="x", full_name="User B")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    assert user.id is not None
    return user.id


@pytest.fixture()
def category(db_session: Session) -> int:
    cat = Category(name="Ăn uống", is_system=True)
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    assert cat.id is not None
    return cat.id


@pytest.fixture()
def _seed_transactions(
    db_session: Session, user_a: int, user_b: int, category: int,
) -> None:
    """Seed transactions cho cả 2 users."""
    today = date.today()
    # User A: 3 transactions
    for i in range(3):
        db_session.add(
            Transaction(
                user_id=user_a,
                category_id=category,
                merchant_name="Grab" if i < 2 else "Highland",
                amount=Decimal("100000") * (i + 1),
                currency="VND",
                transaction_date=today - timedelta(days=i),
            ),
        )
    # User B: 1 transaction
    db_session.add(
        Transaction(
            user_id=user_b,
            category_id=category,
            merchant_name="Starbucks",
            amount=Decimal("500000"),
            currency="VND",
            transaction_date=today,
        ),
    )
    db_session.commit()


class TestQuerySpendingSummary:
    @pytest.mark.usefixtures("_seed_transactions")
    def test_returns_summary(self, db_session: Session, user_a: int) -> None:
        result = query_spending_summary(db_session, user_a, date_range="this_month")
        assert "total_spend" in result
        assert "transaction_count" in result
        assert result["transaction_count"] >= 1
        assert result["currency"] == "VND"

    def test_empty_data(self, db_session: Session, user_a: int) -> None:
        result = query_spending_summary(db_session, user_a, date_range="this_month")
        assert result["transaction_count"] == 0

    @pytest.mark.usefixtures("_seed_transactions")
    def test_user_isolation(self, db_session: Session, user_b: int) -> None:
        result = query_spending_summary(db_session, user_b, date_range="this_month")
        # User B chỉ có 1 transaction 500k
        assert result["transaction_count"] == 1


class TestSearchTransactions:
    @pytest.mark.usefixtures("_seed_transactions")
    def test_search_by_merchant(self, db_session: Session, user_a: int) -> None:
        result = search_transactions(
            db_session, user_a, merchant="Grab", date_range="this_month",
        )
        assert result["total_count"] == 2
        assert len(result["transactions"]) == 2

    @pytest.mark.usefixtures("_seed_transactions")
    def test_search_no_match(self, db_session: Session, user_a: int) -> None:
        result = search_transactions(
            db_session, user_a, merchant="NotExist",
        )
        assert result["total_count"] == 0
        assert result["transactions"] == []

    @pytest.mark.usefixtures("_seed_transactions")
    def test_user_isolation(self, db_session: Session, user_a: int) -> None:
        # User A cannot see Starbucks (belongs to user B)
        result = search_transactions(
            db_session, user_a, merchant="Starbucks",
        )
        assert result["total_count"] == 0

    @pytest.mark.usefixtures("_seed_transactions")
    def test_amount_filter(self, db_session: Session, user_a: int) -> None:
        result = search_transactions(
            db_session, user_a, amount_min=200000,
        )
        # Only transactions >= 200k (200k and 300k)
        assert result["total_count"] == 2


class TestGetBudgetStatus:
    def test_no_budgets(self, db_session: Session, user_a: int) -> None:
        result = get_budget_status(db_session, user_a)
        assert result["budgets"] == []
        assert result["total_budgets"] == 0


class TestComparePeriods:
    @pytest.mark.usefixtures("_seed_transactions")
    def test_compare(self, db_session: Session, user_a: int) -> None:
        result = compare_periods(
            db_session, user_a, period_a="this_month", period_b="last_month",
        )
        assert "period_a" in result
        assert "period_b" in result
        assert "delta_amount" in result
        assert result["currency"] == "VND"


class TestGetTopMerchants:
    @pytest.mark.usefixtures("_seed_transactions")
    def test_returns_merchants(self, db_session: Session, user_a: int) -> None:
        result = get_top_merchants(db_session, user_a, date_range="this_month")
        assert len(result["merchants"]) >= 1
        # Grab should be first (200k total > Highland 300k? No: Grab=100k+200k=300k, Highland=300k)
        # Actually Grab: 100k + 200k = 300k, Highland: 300k — both 300k
        assert result["merchants"][0]["merchant_name"] in ("Grab", "Highland")

    @pytest.mark.usefixtures("_seed_transactions")
    def test_user_isolation(self, db_session: Session, user_a: int) -> None:
        result = get_top_merchants(db_session, user_a, date_range="this_month")
        merchant_names = [m["merchant_name"] for m in result["merchants"]]
        assert "Starbucks" not in merchant_names


class TestGetSpendingByDay:
    @pytest.mark.usefixtures("_seed_transactions")
    def test_returns_days(self, db_session: Session, user_a: int) -> None:
        result = get_spending_by_day(db_session, user_a, date_range="this_month")
        assert len(result["days"]) >= 1
        assert "total_spend" in result

    def test_empty(self, db_session: Session, user_a: int) -> None:
        result = get_spending_by_day(db_session, user_a, date_range="this_month")
        assert result["days"] == []
        assert result["total_spend"] == "0.00"


class TestGetRecentTransactions:
    @pytest.mark.usefixtures("_seed_transactions")
    def test_returns_recent(self, db_session: Session, user_a: int) -> None:
        result = get_recent_transactions(db_session, user_a, limit=2)
        assert result["count"] == 2
        assert len(result["transactions"]) == 2

    def test_empty(self, db_session: Session, user_a: int) -> None:
        result = get_recent_transactions(db_session, user_a)
        assert result["count"] == 0
        assert result["transactions"] == []

    @pytest.mark.usefixtures("_seed_transactions")
    def test_user_isolation(self, db_session: Session, user_b: int) -> None:
        result = get_recent_transactions(db_session, user_b)
        assert result["count"] == 1
        # Only Starbucks for user B
        assert result["transactions"][0]["merchant_name"] == "Starbucks"
