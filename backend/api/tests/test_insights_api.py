"""Tests for row-level Insights APIs."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.models.entities import (
    Budget,
    Category,
    Insight,
    InsightFeedback,
    ReceiptUpload,
    Transaction,
    User,
)
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session, select


def _seed_spending_dataset(session: Session, *, user_id: int) -> dict[str, int]:
    food = Category(user_id=None, name="Ăn uống", is_system=True, color="#f59e0b")
    transport = Category(user_id=None, name="Di chuyển", is_system=True, color="#3b82f6")
    session.add_all([food, transport])
    session.commit()
    session.refresh(food)
    session.refresh(transport)
    assert food.id is not None
    assert transport.id is not None

    session.add_all(
        [
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
            Transaction(
                user_id=user_id,
                category_id=food.id,
                merchant_name="Old Coffee",
                amount=Decimal("20000"),
                currency="VND",
                transaction_date=date(2026, 4, 20),
            ),
        ],
    )
    session.add(
        Budget(
            user_id=user_id,
            category_id=food.id,
            period_month="2026-05",
            amount=Decimal("90000"),
        ),
    )
    session.commit()
    return {"food_id": food.id, "transport_id": transport.id}


def _seed_insight(
    session: Session,
    *,
    user_id: int,
    type_: str = "top_category",
    severity: str = "info",
) -> Insight:
    insight = Insight(
        user_id=user_id,
        type=type_,
        severity=severity,
        title="Ăn uống là danh mục chi nhiều nhất",
        summary="Bạn đã chi nhiều nhất cho Ăn uống.",
        evidence_json='[{"source_type":"transactions"}]',
        actions_json='[{"type":"open_transactions"}]',
        range_start=date(2026, 5, 1),
        range_end=date(2026, 5, 31),
        status="active",
    )
    session.add(insight)
    session.commit()
    session.refresh(insight)
    assert insight.id is not None
    return insight


class TestInsightsAuth:
    def test_list_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/insights")
        assert response.status_code == 401


class TestInsightGeneration:
    def test_generate_uses_transactions_not_unconfirmed_receipt_totals(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        with Session(engine) as session:
            session.add(
                ReceiptUpload(
                    user_id=auth_user.id,
                    file_name="receipt-only.jpg",
                    content_type="image/jpeg",
                    file_size_bytes=123,
                    storage_key="receipts/receipt-only.jpg",
                    merchant_name="Receipt Only",
                    receipt_date=date(2026, 5, 20),
                    total_amount=Decimal("999000"),
                    currency="VND",
                    status="ready",
                    ocr_status="ready",
                ),
            )
            session.commit()

        response = client.post(
            "/api/v1/insights/generate",
            json={"range": "custom", "start_date": "2026-05-01", "end_date": "2026-05-31"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["generated_count"] == 1
        assert body["items"][0]["type"] == "insufficient_data"
        assert body["items"][0]["evidence"][0]["source_type"] == "transactions"
        assert body["items"][0]["evidence"][0]["transaction_count"] == 0

    def test_generate_transaction_backed_insights(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        with Session(engine) as session:
            _seed_spending_dataset(session, user_id=auth_user.id)

        response = client.post(
            "/api/v1/insights/generate",
            json={
                "range": "custom",
                "start_date": "2026-05-01",
                "end_date": "2026-05-31",
                "types": ["top_category", "period_change", "budget_exceeded"],
            },
        )

        assert response.status_code == 200
        body = response.json()
        types = {item["type"] for item in body["items"]}
        assert {"top_category", "period_change", "budget_exceeded"}.issubset(types)
        top = next(item for item in body["items"] if item["type"] == "top_category")
        assert top["evidence"][0]["source_type"] == "transactions"
        assert Decimal(top["evidence"][0]["total_amount"]) == Decimal("100000.00")


class TestInsightCrud:
    def test_list_filters_by_status_type_and_severity(
        self,
        client: TestClient,
        auth_user: User,
        db_session: Session,
    ) -> None:
        assert auth_user.id is not None
        _seed_insight(db_session, user_id=auth_user.id, type_="top_category", severity="watch")
        dismissed = _seed_insight(
            db_session,
            user_id=auth_user.id,
            type_="budget_exceeded",
            severity="danger",
        )
        dismissed.status = "dismissed"
        db_session.add(dismissed)
        db_session.commit()

        response = client.get(
            "/api/v1/insights",
            params={"status": "active", "type": "top_category", "severity": "watch"},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["type"] == "top_category"
        assert body["items"][0]["severity"] == "watch"

    def test_get_detail_respects_ownership(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        with Session(engine) as session:
            other = User(email="other-insight@example.com", password_hash="x")
            session.add(other)
            session.commit()
            session.refresh(other)
            assert other.id is not None
            other_insight = _seed_insight(session, user_id=other.id)

        response = client.get(f"/api/v1/insights/{other_insight.id}")

        assert response.status_code == 404

    def test_dismiss_insight_sets_status_and_timestamp(
        self,
        client: TestClient,
        auth_user: User,
        db_session: Session,
    ) -> None:
        assert auth_user.id is not None
        insight = _seed_insight(db_session, user_id=auth_user.id)

        response = client.patch(f"/api/v1/insights/{insight.id}", json={"status": "dismissed"})

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "dismissed"
        assert body["dismissed_at"] is not None

    def test_feedback_creates_row_and_enforces_ownership(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        with Session(engine) as session:
            insight = _seed_insight(session, user_id=auth_user.id)
            insight_id = insight.id
            other = User(email="feedback-other@example.com", password_hash="x")
            session.add(other)
            session.commit()
            session.refresh(other)
            assert other.id is not None
            other_insight = _seed_insight(session, user_id=other.id)
            other_insight_id = other_insight.id

        response = client.post(
            f"/api/v1/insights/{insight_id}/feedback",
            json={"rating": "helpful", "comment": "Đúng ngữ cảnh"},
        )
        forbidden = client.post(
            f"/api/v1/insights/{other_insight_id}/feedback",
            json={"rating": "helpful"},
        )

        assert response.status_code == 200
        assert forbidden.status_code == 404
        body = response.json()
        assert body["insight_id"] == insight_id
        assert body["rating"] == "helpful"
        with Session(engine) as session:
            rows = session.exec(select(InsightFeedback)).all()
            assert len(rows) == 1
            assert rows[0].user_id == auth_user.id
