"""Tests for billing read APIs."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.models.entities import Insight, Invoice, ReceiptUpload, Transaction, User
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session


class TestBillingAuth:
    def test_plan_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/billing/plan")
        assert response.status_code == 401


class TestBillingReadApis:
    def test_plan_returns_local_development_plan(self, client: TestClient, auth_user: User) -> None:
        response = client.get("/api/v1/billing/plan")

        assert response.status_code == 200
        body = response.json()
        assert body["plan_id"] == "local_dev"
        assert body["status"] == "active"
        assert body["currency"] == "VND"

    def test_usage_counts_current_user_records(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        with Session(engine) as session:
            receipt = ReceiptUpload(
                user_id=auth_user.id,
                file_name="usage.jpg",
                content_type="image/jpeg",
                file_size_bytes=10,
                storage_key="usage.jpg",
                status="ready",
            )
            session.add(receipt)
            session.flush()
            session.add(
                Transaction(
                    user_id=auth_user.id,
                    amount=Decimal("10000"),
                    currency="VND",
                    transaction_date=date(2026, 5, 20),
                ),
            )
            session.add(Invoice(user_id=auth_user.id, receipt_upload_id=receipt.id or 0))
            session.add(
                Insight(
                    user_id=auth_user.id,
                    type="test",
                    severity="info",
                    title="Usage",
                    summary="Usage",
                    range_start=date(2026, 5, 1),
                    range_end=date(2026, 5, 31),
                ),
            )
            other = User(email="billing-other@example.com", password_hash="x")
            session.add(other)
            session.flush()
            session.add(
                Transaction(
                    user_id=other.id or 0,
                    amount=Decimal("999999"),
                    currency="VND",
                    transaction_date=date(2026, 5, 20),
                ),
            )
            session.commit()

        response = client.get("/api/v1/billing/usage")

        assert response.status_code == 200
        body = response.json()
        assert body["transaction_count"] == 1
        assert body["receipt_count"] == 1
        assert body["invoice_count"] == 1
        assert body["insight_count"] == 1

    def test_history_returns_empty_list(self, client: TestClient, auth_user: User) -> None:
        response = client.get("/api/v1/billing/history")

        assert response.status_code == 200
        assert response.json() == {"items": []}

    def test_checkout_session_reports_not_configured(
        self,
        client: TestClient,
        auth_user: User,
    ) -> None:
        response = client.post("/api/v1/billing/checkout-session")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "not_configured"
        assert body["checkout_url"] is None
