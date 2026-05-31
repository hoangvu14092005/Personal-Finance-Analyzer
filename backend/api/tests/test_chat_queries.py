"""Tests cho chat query service layer (Phase 6.1).

Verify:
- Mỗi function trả đúng format.
- User isolation: user A không thấy data user B.
- Empty data trả empty collection, không raise.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from app.models.entities import Category, Invoice, ReceiptUpload, Transaction, User
from app.services.chat.intent_routing import AssistantIntent, classify_assistant_intent
from app.services.chat.queries import (
    compare_periods,
    get_budget_status,
    get_recent_transactions,
    get_spending_by_day,
    get_top_merchants,
    lookup_transaction_receipts,
    query_spending_summary,
    search_receipts,
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


@pytest.fixture()
def _seed_receipts(
    db_session: Session, user_a: int, user_b: int, category: int,
) -> None:
    """Seed receipt evidence with one linked transaction and one isolated upload."""
    receipt = ReceiptUpload(
        user_id=user_a,
        file_name="highlands.jpg",
        content_type="image/jpeg",
        file_size_bytes=1234,
        storage_key="receipts/a/highlands.jpg",
        merchant_name="Highlands Coffee",
        receipt_date=date(2026, 5, 18),
        total_amount=Decimal("68000"),
        currency="VND",
        status="ready",
        ocr_status="ready",
        has_invoice=True,
        created_at=datetime(2026, 5, 19, 8, 30),
    )
    unlinked = ReceiptUpload(
        user_id=user_a,
        file_name="grab.png",
        content_type="image/png",
        file_size_bytes=2345,
        storage_key="receipts/a/grab.png",
        merchant_name="Grab",
        receipt_date=date(2026, 5, 20),
        total_amount=Decimal("42000"),
        currency="VND",
        status="ready",
        ocr_status="ready",
        created_at=datetime(2026, 5, 20, 9, 0),
    )
    other_user = ReceiptUpload(
        user_id=user_b,
        file_name="starbucks.jpg",
        content_type="image/jpeg",
        file_size_bytes=3456,
        storage_key="receipts/b/starbucks.jpg",
        merchant_name="Starbucks",
        receipt_date=date(2026, 5, 18),
        total_amount=Decimal("500000"),
        currency="VND",
        status="ready",
        ocr_status="ready",
        created_at=datetime(2026, 5, 19, 10, 0),
    )
    db_session.add(receipt)
    db_session.add(unlinked)
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(receipt)

    db_session.add(
        Transaction(
            user_id=user_a,
            category_id=category,
            receipt_upload_id=receipt.id,
            merchant_name="Highlands Coffee",
            amount=Decimal("68000"),
            currency="VND",
            transaction_date=date(2026, 5, 18),
            source="ocr",
            status="confirmed",
        ),
    )
    db_session.add(
        Transaction(
            user_id=user_a,
            category_id=category,
            merchant_name="No Receipt Shop",
            amount=Decimal("120000"),
            currency="VND",
            transaction_date=date(2026, 5, 18),
            source="manual",
            status="confirmed",
        ),
    )
    db_session.add(
        Invoice(
            user_id=user_a,
            receipt_upload_id=receipt.id or 0,
            seller_name="Highlands Coffee",
            invoice_number="INV-001",
            issue_date=date(2026, 5, 18),
            grand_total=Decimal("68000"),
            currency="VND",
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


class TestSearchReceipts:
    @pytest.mark.usefixtures("_seed_receipts")
    def test_search_by_receipt_date(self, db_session: Session, user_a: int) -> None:
        result = search_receipts(db_session, user_a, receipt_date="2026-05-18")
        assert result["total_count"] == 1
        assert result["receipts"][0]["merchant_name"] == "Highlands Coffee"
        assert result["receipts"][0]["linked_transaction"]["status"] == "confirmed"

    @pytest.mark.usefixtures("_seed_receipts")
    def test_distinguishes_created_date_from_receipt_date(
        self,
        db_session: Session,
        user_a: int,
    ) -> None:
        by_upload_date = search_receipts(db_session, user_a, created_date="2026-05-19")
        by_receipt_date = search_receipts(db_session, user_a, receipt_date="2026-05-19")

        assert by_upload_date["total_count"] == 1
        assert by_upload_date["receipts"][0]["receipt_date"] == "2026-05-18"
        assert by_receipt_date["total_count"] == 0

    @pytest.mark.usefixtures("_seed_receipts")
    def test_filters_linked_and_invoice_receipts(self, db_session: Session, user_a: int) -> None:
        linked = search_receipts(db_session, user_a, has_transaction=True)
        unlinked = search_receipts(db_session, user_a, has_transaction=False)
        invoices = search_receipts(db_session, user_a, has_invoice=True)

        assert linked["total_count"] == 1
        assert linked["receipts"][0]["linked_transaction"] is not None
        assert unlinked["total_count"] == 1
        assert unlinked["receipts"][0]["linked_transaction"] is None
        assert invoices["total_count"] == 1
        assert invoices["receipts"][0]["invoice_id"] is not None

    @pytest.mark.usefixtures("_seed_receipts")
    def test_user_isolation(self, db_session: Session, user_a: int) -> None:
        result = search_receipts(db_session, user_a, merchant="Starbucks")
        assert result["total_count"] == 0


class TestLookupTransactionReceipts:
    @pytest.mark.usefixtures("_seed_receipts")
    def test_returns_receipt_metadata_for_linked_transaction(
        self,
        db_session: Session,
        user_a: int,
    ) -> None:
        result = lookup_transaction_receipts(
            db_session,
            user_a,
            merchant="Highlands",
            transaction_date="2026-05-18",
        )

        assert result["total_count"] == 1
        tx = result["transactions"][0]
        assert tx["has_receipt"] is True
        assert tx["receipt"]["receipt_id"] is not None
        assert tx["receipt"]["merchant_name"] == "Highlands Coffee"

    @pytest.mark.usefixtures("_seed_receipts")
    def test_can_filter_transactions_without_receipts(
        self,
        db_session: Session,
        user_a: int,
    ) -> None:
        result = lookup_transaction_receipts(
            db_session,
            user_a,
            transaction_date="2026-05-18",
            has_receipt=False,
        )

        assert result["total_count"] == 1
        assert result["transactions"][0]["merchant_name"] == "No Receipt Shop"
        assert result["transactions"][0]["receipt"] is None


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


class TestAssistantIntentRouting:
    def test_routes_spending_questions_to_transaction_intent(self) -> None:
        assert (
            classify_assistant_intent("Hôm qua tôi tiêu bao nhiêu?")
            == AssistantIntent.SPENDING_SUMMARY
        )

    def test_routes_receipt_lookup_questions_to_receipt_intent(self) -> None:
        assert (
            classify_assistant_intent("Xem hóa đơn tôi upload hôm qua")
            == AssistantIntent.RECEIPT_LOOKUP
        )

    def test_routes_transaction_receipt_questions_to_link_intent(self) -> None:
        assert (
            classify_assistant_intent("Giao dịch Highlands hôm qua có hóa đơn không?")
            == AssistantIntent.TRANSACTION_RECEIPT_LOOKUP
        )


class TestNewChatToolsG3:
    """G3 Mục 3a: tool mới products/VAT/diagnose/forecast trên chat layer."""

    @pytest.mark.usefixtures("_seed_transactions")
    def test_diagnose_spending_change_returns_drivers(
        self, db_session: Session, user_a: int,
    ) -> None:
        from app.services.chat.queries import diagnose_spending_change

        result = diagnose_spending_change(db_session, user_a, date_range="this_month")
        assert "drivers" in result
        assert result["currency"] == "VND"

    @pytest.mark.usefixtures("_seed_transactions")
    def test_forecast_month_spending(self, db_session: Session, user_a: int) -> None:
        from app.services.chat.queries import forecast_month_spending

        result = forecast_month_spending(db_session, user_a)
        assert "projected_total" in result
        assert "budgets" in result

    def test_get_tax_summary_empty(self, db_session: Session, user_a: int) -> None:
        from app.services.chat.queries import get_tax_summary

        result = get_tax_summary(db_session, user_a, date_range="this_month")
        assert result["total_tax"] == "0.00"
        assert result["top_sellers"] == []

    def test_get_product_breakdown_empty(self, db_session: Session, user_a: int) -> None:
        from app.services.chat.queries import get_product_breakdown

        result = get_product_breakdown(db_session, user_a, date_range="this_month")
        assert result["products"] == []
        assert result["currency"] == "VND"
