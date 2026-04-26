"""Integration tests cho `GET /api/v1/dashboard/summary` (Phase 4.3).

Verify:
- Auth gate (401 nếu không có cookie).
- Range presets resolve đúng + previous range info.
- Custom range happy + invalid path.
- Empty dataset trả 200 với arrays rỗng.
- Top categories + recent transactions tôn trọng limit.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.models.entities import Category, Transaction, User
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session

SUMMARY_PATH = "/api/v1/dashboard/summary"


def _seed_basic_dataset(engine: Engine, user_id: int) -> dict[str, int]:
    """Seed 3 categories + 4 transactions phân bố qua nhiều ngày để verify
    aggregation. Trả map name → category_id để test assert."""
    with Session(engine) as session:
        food = Category(user_id=None, name="Ăn uống", is_system=True, color="#f59e0b")
        transport = Category(user_id=None, name="Di chuyển", is_system=True, color="#3b82f6")
        misc = Category(user_id=None, name="Khác", is_system=True, color="#a3a3a3")
        session.add_all([food, transport, misc])
        session.commit()
        session.refresh(food)
        session.refresh(transport)
        session.refresh(misc)

        # Hôm nay (test deterministic — dùng ngày trong dataset cố định).
        # 4 transactions trong tháng 4/2026.
        rows = [
            Transaction(
                user_id=user_id,
                category_id=food.id,
                merchant_name="Cafe Hà",
                amount=Decimal("120000"),
                currency="VND",
                transaction_date=date(2026, 4, 10),
            ),
            Transaction(
                user_id=user_id,
                category_id=transport.id,
                merchant_name="Grab",
                amount=Decimal("80000"),
                currency="VND",
                transaction_date=date(2026, 4, 12),
            ),
            Transaction(
                user_id=user_id,
                category_id=food.id,
                merchant_name="Pho 24",
                amount=Decimal("65000"),
                currency="VND",
                transaction_date=date(2026, 4, 13),
            ),
            Transaction(
                user_id=user_id,
                category_id=misc.id,
                merchant_name=None,
                amount=Decimal("35000"),
                currency="VND",
                transaction_date=date(2026, 4, 14),
            ),
        ]
        session.add_all(rows)
        session.commit()

        return {
            "food_id": food.id or 0,
            "transport_id": transport.id or 0,
            "misc_id": misc.id or 0,
        }


class TestDashboardAuth:
    def test_unauthenticated_returns_401(self, client: TestClient) -> None:
        response = client.get(SUMMARY_PATH)
        assert response.status_code == 401


class TestDashboardRangePresets:
    def test_default_range_is_30d(
        self,
        client: TestClient,
        auth_user: User,  # noqa: ARG002
    ) -> None:
        response = client.get(SUMMARY_PATH)
        assert response.status_code == 200
        body = response.json()
        assert body["range"]["preset"] == "30d"
        assert body["range"]["days"] == 30
        assert body["previous_range"]["preset"] == "30d"
        assert body["previous_range"]["days"] == 30

    def test_7d_range_returns_correct_window(
        self,
        client: TestClient,
        auth_user: User,  # noqa: ARG002
    ) -> None:
        response = client.get(SUMMARY_PATH, params={"range": "7d"})
        assert response.status_code == 200
        body = response.json()
        assert body["range"]["preset"] == "7d"
        assert body["range"]["days"] == 7
        # Previous 7d phải cùng độ dài.
        assert body["previous_range"]["days"] == 7

    def test_this_month_previous_is_last_month(
        self,
        client: TestClient,
        auth_user: User,  # noqa: ARG002
    ) -> None:
        response = client.get(SUMMARY_PATH, params={"range": "this_month"})
        assert response.status_code == 200
        body = response.json()
        assert body["range"]["preset"] == "this_month"
        # Previous = full last month → days >= 28.
        assert body["previous_range"]["days"] >= 28

    def test_invalid_preset_returns_400(
        self,
        client: TestClient,
        auth_user: User,  # noqa: ARG002
    ) -> None:
        response = client.get(SUMMARY_PATH, params={"range": "weekly"})
        assert response.status_code == 400
        body = response.json()
        assert "Invalid range preset" in body["detail"]


class TestDashboardCustomRange:
    def test_custom_range_happy_path(
        self,
        client: TestClient,
        auth_user: User,  # noqa: ARG002
    ) -> None:
        response = client.get(
            SUMMARY_PATH,
            params={
                "range": "custom",
                "start_date": "2026-04-01",
                "end_date": "2026-04-15",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["range"]["start"] == "2026-04-01"
        assert body["range"]["end"] == "2026-04-15"
        assert body["range"]["days"] == 15

    def test_custom_range_missing_dates_returns_400(
        self,
        client: TestClient,
        auth_user: User,  # noqa: ARG002
    ) -> None:
        response = client.get(SUMMARY_PATH, params={"range": "custom"})
        assert response.status_code == 400
        body = response.json()
        assert "Custom preset requires" in body["detail"]

    def test_custom_range_start_after_end_returns_400(
        self,
        client: TestClient,
        auth_user: User,  # noqa: ARG002
    ) -> None:
        response = client.get(
            SUMMARY_PATH,
            params={
                "range": "custom",
                "start_date": "2026-04-15",
                "end_date": "2026-04-01",
            },
        )
        assert response.status_code == 400


class TestDashboardAggregation:
    def test_summary_totals_match_seeded_data(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        _seed_basic_dataset(engine, auth_user.id)

        # Dùng custom range bao trùm seeded data: 2026-04-01 ~ 2026-04-15.
        response = client.get(
            SUMMARY_PATH,
            params={
                "range": "custom",
                "start_date": "2026-04-01",
                "end_date": "2026-04-15",
            },
        )
        assert response.status_code == 200
        body = response.json()
        # 120k + 80k + 65k + 35k = 300k.
        assert Decimal(body["current"]["total_spend"]) == Decimal("300000")
        assert body["current"]["transaction_count"] == 4

    def test_top_categories_ordered_with_percentage(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        _seed_basic_dataset(engine, auth_user.id)

        response = client.get(
            SUMMARY_PATH,
            params={
                "range": "custom",
                "start_date": "2026-04-01",
                "end_date": "2026-04-15",
            },
        )
        body = response.json()
        cats = body["top_categories"]
        # 3 categories: Ăn uống (185k), Di chuyển (80k), Khác (35k).
        assert len(cats) == 3
        assert cats[0]["name"] == "Ăn uống"
        assert Decimal(cats[0]["total_amount"]) == Decimal("185000")
        # 185k / 300k * 100 ≈ 61.67%.
        assert abs(cats[0]["percentage"] - 61.67) < 0.05
        assert cats[0]["color"] == "#f59e0b"

    def test_top_categories_limit_enforced(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        _seed_basic_dataset(engine, auth_user.id)

        response = client.get(
            SUMMARY_PATH,
            params={
                "range": "custom",
                "start_date": "2026-04-01",
                "end_date": "2026-04-15",
                "top_categories_limit": 2,
            },
        )
        body = response.json()
        assert len(body["top_categories"]) == 2
        assert body["top_categories"][0]["name"] == "Ăn uống"

    def test_recent_transactions_ordered_desc(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        _seed_basic_dataset(engine, auth_user.id)

        response = client.get(
            SUMMARY_PATH,
            params={
                "range": "custom",
                "start_date": "2026-04-01",
                "end_date": "2026-04-15",
                "recent_transactions_limit": 10,
            },
        )
        body = response.json()
        recent = body["recent_transactions"]
        assert len(recent) == 4
        dates = [tx["transaction_date"] for tx in recent]
        assert dates == sorted(dates, reverse=True)
        # Tx mới nhất (2026-04-14) là Khác category.
        assert recent[0]["category_name"] == "Khác"

    def test_limit_cap_returns_422_when_too_high(
        self,
        client: TestClient,
        auth_user: User,  # noqa: ARG002
    ) -> None:
        # FastAPI Query(le=20) → 422 khi vượt cap.
        response = client.get(
            SUMMARY_PATH,
            params={"top_categories_limit": 100},
        )
        assert response.status_code == 422


class TestDashboardEmptyState:
    def test_empty_dataset_returns_zeros(
        self,
        client: TestClient,
        auth_user: User,  # noqa: ARG002
    ) -> None:
        response = client.get(SUMMARY_PATH, params={"range": "30d"})
        assert response.status_code == 200
        body = response.json()
        assert Decimal(body["current"]["total_spend"]) == Decimal("0")
        assert body["current"]["transaction_count"] == 0
        assert body["top_categories"] == []
        assert body["recent_transactions"] == []
        assert Decimal(body["delta_amount"]) == Decimal("0")
        assert body["delta_percent"] is None
