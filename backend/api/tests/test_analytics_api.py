"""Integration tests for canonical `/api/v1/analytics/*` endpoints."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.models.entities import Budget, Category, ReceiptUpload, Transaction, User
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session


def _seed_analytics_dataset(engine: Engine, user_id: int) -> dict[str, int]:
    with Session(engine) as session:
        food = Category(user_id=None, name="Ăn uống", is_system=True, color="#f59e0b")
        transport = Category(user_id=None, name="Di chuyển", is_system=True, color="#3b82f6")
        session.add_all([food, transport])
        session.commit()
        session.refresh(food)
        session.refresh(transport)

        rows = [
            Transaction(
                user_id=user_id,
                category_id=food.id,
                merchant_name="Highlands Coffee",
                amount=Decimal("68000"),
                currency="VND",
                transaction_date=date(2026, 5, 18),
            ),
            Transaction(
                user_id=user_id,
                category_id=food.id,
                merchant_name="Highlands Coffee",
                amount=Decimal("32000"),
                currency="VND",
                transaction_date=date(2026, 5, 19),
            ),
            Transaction(
                user_id=user_id,
                category_id=transport.id,
                merchant_name="Grab",
                amount=Decimal("50000"),
                currency="VND",
                transaction_date=date(2026, 5, 20),
            ),
        ]
        session.add_all(rows)
        session.add(
            ReceiptUpload(
                user_id=user_id,
                file_name="unconfirmed.jpg",
                content_type="image/jpeg",
                file_size_bytes=123,
                storage_key="receipts/unconfirmed.jpg",
                merchant_name="Receipt Only",
                receipt_date=date(2026, 5, 20),
                total_amount=Decimal("999000"),
                currency="VND",
                status="ready",
                ocr_status="ready",
            ),
        )
        session.add(
            Budget(
                user_id=user_id,
                category_id=food.id or 0,
                period_month="2026-05",
                amount=Decimal("120000"),
            ),
        )
        session.commit()
        return {"food_id": food.id or 0, "transport_id": transport.id or 0}


class TestAnalyticsAuth:
    def test_overview_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/analytics/overview")
        assert response.status_code == 401


class TestAnalyticsOverview:
    def test_overview_uses_confirmed_transactions_not_receipt_totals(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        _seed_analytics_dataset(engine, auth_user.id)

        response = client.get(
            "/api/v1/analytics/overview",
            params={"range": "custom", "start_date": "2026-05-01", "end_date": "2026-05-31"},
        )

        assert response.status_code == 200
        body = response.json()
        assert Decimal(body["current"]["total_spend"]) == Decimal("150000")
        assert body["current"]["transaction_count"] == 3


class TestAnalyticsCategories:
    def test_categories_returns_ranked_breakdown(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        _seed_analytics_dataset(engine, auth_user.id)

        response = client.get(
            "/api/v1/analytics/categories",
            params={"range": "custom", "start_date": "2026-05-01", "end_date": "2026-05-31"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["range"]["preset"] == "custom"
        assert body["items"][0]["name"] == "Ăn uống"
        assert Decimal(body["items"][0]["total_amount"]) == Decimal("100000")


class TestAnalyticsMerchants:
    def test_merchants_returns_ranked_breakdown(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        _seed_analytics_dataset(engine, auth_user.id)

        response = client.get(
            "/api/v1/analytics/merchants",
            params={"range": "custom", "start_date": "2026-05-01", "end_date": "2026-05-31"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["items"][0]["merchant_name"] == "Highlands Coffee"
        assert Decimal(body["items"][0]["total_amount"]) == Decimal("100000")
        assert body["items"][0]["transaction_count"] == 2


class TestAnalyticsTrends:
    def test_trends_returns_daily_series_from_transactions_only(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        _seed_analytics_dataset(engine, auth_user.id)

        response = client.get(
            "/api/v1/analytics/trends",
            params={"range": "custom", "start_date": "2026-05-18", "end_date": "2026-05-20"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["group_by"] == "day"
        assert [point["period_start"] for point in body["points"]] == [
            "2026-05-18",
            "2026-05-19",
            "2026-05-20",
        ]
        assert sum(Decimal(point["amount"]) for point in body["points"]) == Decimal("150000")


class TestAnalyticsCalendar:
    def test_calendar_returns_day_cells_with_top_category(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        _seed_analytics_dataset(engine, auth_user.id)

        response = client.get(
            "/api/v1/analytics/calendar",
            params={"range": "custom", "start_date": "2026-05-18", "end_date": "2026-05-20"},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["days"]) == 3
        may_20 = body["days"][2]
        assert may_20["date"] == "2026-05-20"
        assert Decimal(may_20["amount"]) == Decimal("50000")
        assert may_20["transaction_count"] == 1
        assert may_20["top_category_name"] == "Di chuyển"
        assert body["legend"]["levels"]["4"] == "unusual"


class TestAnalyticsAnomalies:
    def test_anomalies_flags_large_transactions(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        ids = _seed_analytics_dataset(engine, auth_user.id)
        with Session(engine) as session:
            session.add(
                Transaction(
                    user_id=auth_user.id,
                    category_id=ids["food_id"],
                    merchant_name="Laptop Store",
                    amount=Decimal("900000"),
                    currency="VND",
                    transaction_date=date(2026, 5, 21),
                ),
            )
            session.commit()

        response = client.get(
            "/api/v1/analytics/anomalies",
            params={"range": "custom", "start_date": "2026-05-01", "end_date": "2026-05-31"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["anomalies"][0]["type"] == "large_transaction"
        assert body["anomalies"][0]["merchant_name"] == "Laptop Store"
        assert Decimal(body["anomalies"][0]["amount"]) == Decimal("900000")


class TestAnalyticsInsightFeed:
    def test_insight_feed_autogenerates_from_transaction_evidence(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        _seed_analytics_dataset(engine, auth_user.id)

        response = client.get(
            "/api/v1/analytics/insight-feed",
            params={"range": "custom", "start_date": "2026-05-01", "end_date": "2026-05-31"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["source"] == "generated"
        assert body["hero"]["type"] == "top_category"
        assert body["hero"]["evidence"][0]["source_type"] == "transactions"


class TestAnalyticsBudgets:
    def test_budgets_returns_summary_and_rows(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        _seed_analytics_dataset(engine, auth_user.id)

        response = client.get(
            "/api/v1/analytics/budgets",
            params={"period_month": "2026-05"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["period_month"] == "2026-05"
        assert Decimal(body["total_budget"]) == Decimal("120000")
        assert Decimal(body["total_spent"]) == Decimal("100000")
        assert body["warning_count"] == 1
        assert body["exceeded_count"] == 0
        assert len(body["budgets"]) == 1
