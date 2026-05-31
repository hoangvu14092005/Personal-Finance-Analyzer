"""Tests cho G3: diagnostics + forecast (service + endpoint)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.models.entities import Budget, Category, Transaction, User
from app.services.date_ranges import DateRange
from app.services.diagnostics import compute_spending_diagnostics
from app.services.forecast import compute_forecast
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session


def _seed_two_period_dataset(engine: Engine, user_id: int) -> dict[str, int]:
    """Kỳ hiện tại (tháng 5) chi nhiều hơn kỳ trước (tháng 4), chủ yếu do Ăn uống."""
    with Session(engine) as session:
        food = Category(user_id=None, name="Ăn uống", is_system=True)
        transport = Category(user_id=None, name="Di chuyển", is_system=True)
        session.add_all([food, transport])
        session.commit()
        session.refresh(food)
        session.refresh(transport)

        def _tx(cat_id: int | None, merchant: str, amount: str, d: date) -> Transaction:
            return Transaction(
                user_id=user_id,
                category_id=cat_id,
                merchant_name=merchant,
                amount=Decimal(amount),
                currency="VND",
                transaction_date=d,
            )

        rows = [
            # Kỳ trước (tháng 4): food 100k, transport 50k
            _tx(food.id, "Highlands", "100000", date(2026, 4, 10)),
            _tx(transport.id, "Grab", "50000", date(2026, 4, 12)),
            # Kỳ hiện tại (tháng 5): food 300k (tăng mạnh do Highlands), transport 50k
            _tx(food.id, "Highlands", "250000", date(2026, 5, 10)),
            _tx(food.id, "KFC", "50000", date(2026, 5, 11)),
            _tx(transport.id, "Grab", "50000", date(2026, 5, 12)),
        ]
        session.add_all(rows)
        session.commit()
        return {"food_id": food.id or 0, "transport_id": transport.id or 0}


class TestDiagnosticsService:
    def test_identifies_top_driver_category_and_merchant(self, engine: Engine) -> None:
        with Session(engine) as session:
            user = User(email="d@test.com", password_hash="x")
            session.add(user)
            session.commit()
            session.refresh(user)
            uid = user.id
            assert uid is not None
        _seed_two_period_dataset(engine, uid)

        current = DateRange(start=date(2026, 5, 1), end=date(2026, 5, 31))
        previous = DateRange(start=date(2026, 4, 1), end=date(2026, 4, 30))
        with Session(engine) as session:
            diag = compute_spending_diagnostics(session, uid, current, previous)

        assert diag.current_total == Decimal("350000")
        assert diag.previous_total == Decimal("150000")
        assert diag.delta_amount == Decimal("200000")
        # Driver lớn nhất phải là Ăn uống (tăng 200k).
        top = diag.drivers[0]
        assert top.category_name == "Ăn uống"
        assert top.direction == "increase"
        assert top.delta_amount == Decimal("200000")
        # Merchant đóng góp chính là Highlands.
        assert top.top_merchants[0].merchant_name == "Highlands"


class TestForecastService:
    def test_run_rate_projection(self, engine: Engine) -> None:
        with Session(engine) as session:
            user = User(email="f@test.com", password_hash="x")
            session.add(user)
            session.commit()
            session.refresh(user)
            uid = user.id
            assert uid is not None
            # Đã chi 100k trong 10 ngày đầu tháng 5.
            session.add(
                Transaction(user_id=uid, amount=Decimal("100000"), currency="VND",
                            transaction_date=date(2026, 5, 5)),
            )
            session.commit()

        with Session(engine) as session:
            forecast = compute_forecast(session, uid, today=date(2026, 5, 10))

        # 100k / 10 ngày = 10k/ngày × 31 ngày = 310k.
        assert forecast.month.spent_so_far == Decimal("100000")
        assert forecast.month.days_elapsed == 10
        assert forecast.month.days_in_month == 31
        assert forecast.month.projected_total == Decimal("310000")

    def test_budget_will_exceed_warning(self, engine: Engine) -> None:
        with Session(engine) as session:
            user = User(email="f2@test.com", password_hash="x")
            session.add(user)
            session.commit()
            session.refresh(user)
            uid = user.id
            assert uid is not None
            cat = Category(user_id=None, name="Ăn uống", is_system=True)
            session.add(cat)
            session.commit()
            session.refresh(cat)
            # Budget 200k, đã chi 100k trong 10 ngày → dự báo 310k > 200k.
            session.add(Budget(user_id=uid, category_id=cat.id or 0,
                               period_month="2026-05", amount=Decimal("200000")))
            session.add(Transaction(user_id=uid, category_id=cat.id, amount=Decimal("100000"),
                                    currency="VND", transaction_date=date(2026, 5, 5)))
            session.commit()

        with Session(engine) as session:
            forecast = compute_forecast(session, uid, today=date(2026, 5, 10))

        assert len(forecast.budgets) == 1
        b = forecast.budgets[0]
        assert b.status == "will_exceed"
        assert b.projected_spend == Decimal("310000")
        assert b.projected_exceed_date is not None


class TestAnalyticsG3Endpoints:
    def test_diagnostics_requires_auth(self, client: TestClient) -> None:
        assert client.get("/api/v1/analytics/diagnostics").status_code == 401

    def test_forecast_requires_auth(self, client: TestClient) -> None:
        assert client.get("/api/v1/analytics/forecast").status_code == 401

    def test_diagnostics_endpoint(
        self, engine: Engine, client: TestClient, auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        _seed_two_period_dataset(engine, auth_user.id)
        resp = client.get(
            "/api/v1/analytics/diagnostics"
            "?range=custom&start_date=2026-05-01&end_date=2026-05-31",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "drivers" in body
        assert body["drivers"][0]["category_name"] == "Ăn uống"

    def test_forecast_endpoint(
        self, engine: Engine, client: TestClient, auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        resp = client.get("/api/v1/analytics/forecast")
        assert resp.status_code == 200
        body = resp.json()
        assert "month" in body
        assert "budgets" in body
