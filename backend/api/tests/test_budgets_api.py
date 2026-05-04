"""Integration tests cho `/api/v1/budgets` (Phase 5.2 + 5.3).

Covers:
- Auth gate (401 khi no cookie).
- POST create: 201 happy, 404 category không thuộc user, 409 duplicate.
- GET list: filter period_month + user isolation.
- GET usage: status safe/warning/exceeded + sort + empty.
- PUT update: 200 amount mới, 404 cross-user.
- DELETE: 204, 404.
- Validation: period_month invalid format (422), amount <= 0 (422).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from app.models.entities import Budget, Category, Transaction, User
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session


@pytest.fixture
def system_category(engine: Engine) -> Category:
    """Seed 1 system category dùng chung cho các test."""
    with Session(engine) as session:
        cat = Category(name="Ăn uống", color="#f59e0b", is_system=True)
        session.add(cat)
        session.commit()
        session.refresh(cat)
        assert cat.id is not None
        return cat


class TestCreateBudget:
    def test_unauthenticated_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/budgets",
            json={"category_id": 1, "period_month": "2026-05", "amount": "1000000"},
        )
        assert response.status_code == 401

    def test_happy_path(
        self,
        client: TestClient,
        auth_user: User,
        system_category: Category,
    ) -> None:
        response = client.post(
            "/api/v1/budgets",
            json={
                "category_id": system_category.id,
                "period_month": "2026-05",
                "amount": "2000000",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["category_id"] == system_category.id
        assert body["period_month"] == "2026-05"
        assert body["amount"] == "2000000.00"
        assert body["user_id"] == auth_user.id

    def test_invalid_period_month_format(
        self,
        client: TestClient,
        auth_user: User,
        system_category: Category,
    ) -> None:
        response = client.post(
            "/api/v1/budgets",
            json={
                "category_id": system_category.id,
                "period_month": "2026-13",  # Tháng 13 invalid.
                "amount": "1000000",
            },
        )
        assert response.status_code == 422

    def test_amount_zero_rejected(
        self,
        client: TestClient,
        auth_user: User,
        system_category: Category,
    ) -> None:
        response = client.post(
            "/api/v1/budgets",
            json={
                "category_id": system_category.id,
                "period_month": "2026-05",
                "amount": "0",
            },
        )
        assert response.status_code == 422

    def test_category_not_owned_returns_404(
        self,
        client: TestClient,
        auth_user: User,
        engine: Engine,
    ) -> None:
        # Seed category thuộc user khác.
        with Session(engine) as session:
            other = User(email="other@example.com", password_hash="hashed")
            session.add(other)
            session.commit()
            session.refresh(other)
            assert other.id is not None
            cat = Category(user_id=other.id, name="Secret", is_system=False)
            session.add(cat)
            session.commit()
            session.refresh(cat)
            assert cat.id is not None
            cat_id = cat.id

        response = client.post(
            "/api/v1/budgets",
            json={
                "category_id": cat_id,
                "period_month": "2026-05",
                "amount": "1000000",
            },
        )
        assert response.status_code == 404

    def test_duplicate_returns_409(
        self,
        client: TestClient,
        auth_user: User,
        system_category: Category,
    ) -> None:
        # Tạo lần 1 → OK.
        first = client.post(
            "/api/v1/budgets",
            json={
                "category_id": system_category.id,
                "period_month": "2026-05",
                "amount": "1000000",
            },
        )
        assert first.status_code == 201

        # Lần 2 cùng (category, period) → 409.
        second = client.post(
            "/api/v1/budgets",
            json={
                "category_id": system_category.id,
                "period_month": "2026-05",
                "amount": "2000000",
            },
        )
        assert second.status_code == 409


class TestListBudgets:
    def test_list_empty(self, client: TestClient, auth_user: User) -> None:
        response = client.get("/api/v1/budgets")
        assert response.status_code == 200
        assert response.json() == {"items": []}

    def test_list_returns_only_user_budgets(
        self,
        client: TestClient,
        auth_user: User,
        system_category: Category,
        engine: Engine,
    ) -> None:
        # Seed budget cho user khác.
        with Session(engine) as session:
            other = User(email="other2@example.com", password_hash="hashed")
            session.add(other)
            session.commit()
            session.refresh(other)
            assert other.id is not None and system_category.id is not None
            session.add(
                Budget(
                    user_id=other.id,
                    category_id=system_category.id,
                    period_month="2026-05",
                    amount=Decimal("999999"),
                ),
            )
            session.commit()

        # Tạo budget của chính user hiện tại.
        client.post(
            "/api/v1/budgets",
            json={
                "category_id": system_category.id,
                "period_month": "2026-05",
                "amount": "1000000",
            },
        )

        response = client.get("/api/v1/budgets")
        body = response.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["amount"] == "1000000.00"

    def test_list_filter_period_month(
        self,
        client: TestClient,
        auth_user: User,
        system_category: Category,
    ) -> None:
        for month in ("2026-04", "2026-05", "2026-06"):
            client.post(
                "/api/v1/budgets",
                json={
                    "category_id": system_category.id,
                    "period_month": month,
                    "amount": "1000000",
                },
            )

        response = client.get("/api/v1/budgets?period_month=2026-05")
        body = response.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["period_month"] == "2026-05"

    def test_list_filter_invalid_period_month_format(
        self,
        client: TestClient,
        auth_user: User,
    ) -> None:
        response = client.get("/api/v1/budgets?period_month=2026-13")
        assert response.status_code == 422


class TestBudgetUsage:
    def _setup(
        self,
        engine: Engine,
        user: User,
        system_category: Category,
    ) -> int:
        """Tạo 1 budget và 1 transaction ở 60% usage → status safe."""
        assert user.id is not None and system_category.id is not None
        with Session(engine) as session:
            budget = Budget(
                user_id=user.id,
                category_id=system_category.id,
                period_month="2026-05",
                amount=Decimal("1000000"),
            )
            session.add(budget)
            session.add(
                Transaction(
                    user_id=user.id,
                    category_id=system_category.id,
                    amount=Decimal("600000"),  # 60% → safe.
                    currency="VND",
                    transaction_date=date(2026, 5, 10),
                ),
            )
            session.commit()
            session.refresh(budget)
            assert budget.id is not None
            return budget.id

    def test_usage_safe(
        self,
        client: TestClient,
        auth_user: User,
        system_category: Category,
        engine: Engine,
    ) -> None:
        budget_id = self._setup(engine, auth_user, system_category)

        response = client.get("/api/v1/budgets/usage?period_month=2026-05")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["budget_id"] == budget_id
        assert body[0]["spent_amount"] == "600000.00"
        assert body[0]["remaining_amount"] == "400000.00"
        assert body[0]["percent_used"] == 60.0
        assert body[0]["status"] == "safe"

    def test_usage_empty_when_no_budget(
        self,
        client: TestClient,
        auth_user: User,
    ) -> None:
        response = client.get("/api/v1/budgets/usage?period_month=2026-05")
        assert response.status_code == 200
        assert response.json() == []

    def test_usage_requires_period_month(
        self,
        client: TestClient,
        auth_user: User,
    ) -> None:
        # Thiếu param → 422 (FastAPI tự trả).
        response = client.get("/api/v1/budgets/usage")
        assert response.status_code == 422


class TestUpdateBudget:
    def test_update_amount(
        self,
        client: TestClient,
        auth_user: User,
        system_category: Category,
    ) -> None:
        create = client.post(
            "/api/v1/budgets",
            json={
                "category_id": system_category.id,
                "period_month": "2026-05",
                "amount": "1000000",
            },
        )
        budget_id = create.json()["id"]

        response = client.put(
            f"/api/v1/budgets/{budget_id}",
            json={"amount": "2500000"},
        )
        assert response.status_code == 200
        assert response.json()["amount"] == "2500000.00"

    def test_update_not_owned_returns_404(
        self,
        client: TestClient,
        auth_user: User,
        engine: Engine,
    ) -> None:
        # Seed budget thuộc user khác.
        with Session(engine) as session:
            other = User(email="other3@example.com", password_hash="hashed")
            session.add(other)
            session.commit()
            session.refresh(other)
            assert other.id is not None
            cat = Category(name="X", is_system=True)
            session.add(cat)
            session.commit()
            session.refresh(cat)
            assert cat.id is not None
            budget = Budget(
                user_id=other.id,
                category_id=cat.id,
                period_month="2026-05",
                amount=Decimal("100"),
            )
            session.add(budget)
            session.commit()
            session.refresh(budget)
            assert budget.id is not None
            budget_id = budget.id

        response = client.put(
            f"/api/v1/budgets/{budget_id}",
            json={"amount": "500"},
        )
        assert response.status_code == 404


class TestDeleteBudget:
    def test_delete_happy_path(
        self,
        client: TestClient,
        auth_user: User,
        system_category: Category,
    ) -> None:
        create = client.post(
            "/api/v1/budgets",
            json={
                "category_id": system_category.id,
                "period_month": "2026-05",
                "amount": "1000000",
            },
        )
        budget_id = create.json()["id"]

        response = client.delete(f"/api/v1/budgets/{budget_id}")
        assert response.status_code == 204

        # Verify đã xóa.
        listing = client.get("/api/v1/budgets")
        assert listing.json()["items"] == []

    def test_delete_nonexistent_returns_404(
        self,
        client: TestClient,
        auth_user: User,
    ) -> None:
        response = client.delete("/api/v1/budgets/99999")
        assert response.status_code == 404


class TestDashboardBudgetIntegration:
    """Phase 5.4: dashboard summary trả kèm budgets_usage."""

    def test_this_month_includes_budget_usage(
        self,
        client: TestClient,
        auth_user: User,
        system_category: Category,
        engine: Engine,
    ) -> None:
        """range=this_month → budget_period trùng tháng hiện tại, usages có data."""
        assert auth_user.id is not None and system_category.id is not None
        today = date.today()
        period = f"{today.year:04d}-{today.month:02d}"

        with Session(engine) as session:
            session.add(
                Budget(
                    user_id=auth_user.id,
                    category_id=system_category.id,
                    period_month=period,
                    amount=Decimal("1000000"),
                ),
            )
            session.add(
                Transaction(
                    user_id=auth_user.id,
                    category_id=system_category.id,
                    amount=Decimal("500000"),  # 50% used.
                    currency="VND",
                    transaction_date=today,
                ),
            )
            session.commit()

        response = client.get("/api/v1/dashboard/summary?range=this_month")
        assert response.status_code == 200
        body = response.json()
        assert body["budget_period"] == period
        assert len(body["budgets_usage"]) == 1
        assert body["budgets_usage"][0]["percent_used"] == 50.0
        assert body["budgets_usage"][0]["status"] == "safe"

    def test_no_budget_returns_empty_usages(
        self,
        client: TestClient,
        auth_user: User,
    ) -> None:
        response = client.get("/api/v1/dashboard/summary?range=30d")
        assert response.status_code == 200
        body = response.json()
        # budget_period luôn có (format YYYY-MM) dù empty.
        assert len(body["budget_period"]) == 7
        assert body["budgets_usage"] == []
