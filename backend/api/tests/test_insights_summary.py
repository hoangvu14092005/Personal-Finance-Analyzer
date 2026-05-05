"""Tests cho `services.insights.summary` (Phase 6.1).

Focus:
- `SummaryInput.fingerprint` stable với cùng dữ liệu.
- `SummaryInput.to_dict` schema đúng key & Decimal serialize 2 digits.
- `_collect_anomalies`: flag đúng giao dịch vượt 3x median.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from app.models.entities import Category, Transaction, User
from app.services.analytics import compute_summary
from app.services.date_ranges import DateRange
from app.services.insights.summary import (
    ANOMALY_MAX_ITEMS,
    build_summary_input,
    safe_delta_percent,
)
from sqlmodel import Session


@pytest.fixture
def seed_user(db_session: Session) -> User:
    user = User(email="summary@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def seed_category(db_session: Session) -> Category:
    cat = Category(user_id=None, name="Ăn uống", is_system=True, color="#f59e0b")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


def _seed_txn(
    session: Session,
    user_id: int,
    category_id: int | None,
    *,
    amount: str,
    day: int,
) -> None:
    session.add(
        Transaction(
            user_id=user_id,
            category_id=category_id,
            merchant_name=f"M-{day}",
            amount=Decimal(amount),
            currency="VND",
            transaction_date=date(2026, 4, day),
        ),
    )


class TestFingerprint:
    def test_stable_same_data(
        self,
        db_session: Session,
        seed_user: User,
        seed_category: Category,
    ) -> None:
        """Same DB state → cùng fingerprint giữa 2 lần build."""
        assert seed_user.id is not None
        for d in range(1, 6):
            _seed_txn(
                db_session,
                seed_user.id,
                seed_category.id,
                amount="100000",
                day=d,
            )
        db_session.commit()

        current = DateRange(date(2026, 4, 1), date(2026, 4, 30))
        previous = DateRange(date(2026, 3, 2), date(2026, 3, 31))
        analytics_1 = compute_summary(db_session, seed_user.id, current, previous)
        s1 = build_summary_input(
            db_session, seed_user.id, "30d", current, analytics_1,
        )
        analytics_2 = compute_summary(db_session, seed_user.id, current, previous)
        s2 = build_summary_input(
            db_session, seed_user.id, "30d", current, analytics_2,
        )
        assert s1.fingerprint() == s2.fingerprint()

    def test_changes_when_amount_changes(
        self,
        db_session: Session,
        seed_user: User,
        seed_category: Category,
    ) -> None:
        assert seed_user.id is not None
        for d in range(1, 6):
            _seed_txn(
                db_session,
                seed_user.id,
                seed_category.id,
                amount="100000",
                day=d,
            )
        db_session.commit()

        current = DateRange(date(2026, 4, 1), date(2026, 4, 30))
        previous = DateRange(date(2026, 3, 2), date(2026, 3, 31))
        analytics = compute_summary(db_session, seed_user.id, current, previous)
        fp_before = build_summary_input(
            db_session, seed_user.id, "30d", current, analytics,
        ).fingerprint()

        # Thêm 1 transaction mới → total + count đổi → fingerprint đổi.
        _seed_txn(
            db_session,
            seed_user.id,
            seed_category.id,
            amount="77777",
            day=15,
        )
        db_session.commit()

        analytics_2 = compute_summary(db_session, seed_user.id, current, previous)
        fp_after = build_summary_input(
            db_session, seed_user.id, "30d", current, analytics_2,
        ).fingerprint()
        assert fp_before != fp_after


class TestToDict:
    def test_decimal_format(
        self,
        db_session: Session,
        seed_user: User,
        seed_category: Category,
    ) -> None:
        """Decimal phải được format 2 digits — không bị "100000" hoặc "1e5"."""
        assert seed_user.id is not None
        for d in range(1, 6):
            _seed_txn(
                db_session,
                seed_user.id,
                seed_category.id,
                amount="100000",
                day=d,
            )
        db_session.commit()

        current = DateRange(date(2026, 4, 1), date(2026, 4, 30))
        previous = DateRange(date(2026, 3, 2), date(2026, 3, 31))
        analytics = compute_summary(db_session, seed_user.id, current, previous)
        summary = build_summary_input(
            db_session, seed_user.id, "30d", current, analytics,
        )
        data = summary.to_dict()
        assert data["current"]["total_spend"] == "500000.00"
        # Range keys.
        assert data["range"] == {
            "preset": "30d",
            "start": "2026-04-01",
            "end": "2026-04-30",
            "days": 30,
        }


class TestAnomalies:
    def test_flags_large_transaction(
        self,
        db_session: Session,
        seed_user: User,
        seed_category: Category,
    ) -> None:
        """1 giao dịch 1,000,000 giữa dataset median 100k → flag."""
        assert seed_user.id is not None
        for d in range(1, 6):
            _seed_txn(
                db_session,
                seed_user.id,
                seed_category.id,
                amount="100000",
                day=d,
            )
        # Outlier.
        _seed_txn(
            db_session,
            seed_user.id,
            seed_category.id,
            amount="1000000",
            day=20,
        )
        db_session.commit()

        current = DateRange(date(2026, 4, 1), date(2026, 4, 30))
        previous = DateRange(date(2026, 3, 2), date(2026, 3, 31))
        analytics = compute_summary(db_session, seed_user.id, current, previous)
        summary = build_summary_input(
            db_session, seed_user.id, "30d", current, analytics,
        )
        assert len(summary.anomalies) == 1
        anomaly = summary.anomalies[0]
        assert anomaly.amount == Decimal("1000000")
        assert anomaly.kind == "large_transaction"

    def test_no_anomaly_when_uniform(
        self,
        db_session: Session,
        seed_user: User,
        seed_category: Category,
    ) -> None:
        """Tất cả cùng 100k → không có anomaly (< 3x median)."""
        assert seed_user.id is not None
        for d in range(1, 11):
            _seed_txn(
                db_session,
                seed_user.id,
                seed_category.id,
                amount="100000",
                day=d,
            )
        db_session.commit()

        current = DateRange(date(2026, 4, 1), date(2026, 4, 30))
        previous = DateRange(date(2026, 3, 2), date(2026, 3, 31))
        analytics = compute_summary(db_session, seed_user.id, current, previous)
        summary = build_summary_input(
            db_session, seed_user.id, "30d", current, analytics,
        )
        assert summary.anomalies == []

    def test_caps_at_max(
        self,
        db_session: Session,
        seed_user: User,
        seed_category: Category,
    ) -> None:
        """Nhiều outlier → chỉ lấy tối đa ANOMALY_MAX_ITEMS."""
        assert seed_user.id is not None
        for d in range(1, 11):
            _seed_txn(
                db_session,
                seed_user.id,
                seed_category.id,
                amount="100000",
                day=d,
            )
        # 10 outlier = 5 triệu.
        for d in range(11, 21):
            _seed_txn(
                db_session,
                seed_user.id,
                seed_category.id,
                amount="5000000",
                day=d,
            )
        db_session.commit()

        current = DateRange(date(2026, 4, 1), date(2026, 4, 30))
        previous = DateRange(date(2026, 3, 2), date(2026, 3, 31))
        analytics = compute_summary(db_session, seed_user.id, current, previous)
        summary = build_summary_input(
            db_session, seed_user.id, "30d", current, analytics,
        )
        assert len(summary.anomalies) <= ANOMALY_MAX_ITEMS


class TestSafeDeltaPercent:
    def test_zero_previous(self) -> None:
        assert safe_delta_percent(Decimal("100"), Decimal("0")) is None

    def test_increase(self) -> None:
        assert safe_delta_percent(Decimal("150"), Decimal("100")) == 50.0

    def test_decrease(self) -> None:
        assert safe_delta_percent(Decimal("80"), Decimal("100")) == -20.0
