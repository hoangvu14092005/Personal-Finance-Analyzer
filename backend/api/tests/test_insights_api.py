"""Integration tests cho `/api/v1/insights/*` (Phase 6.9).

Covers:
- POST /generate: ready / insufficient_data / cache-hit / force-refresh.
- GET /latest: 404 khi chưa có snapshot, 200 khi đã generate.
- Auth required (401 khi thiếu cookie).
- Schema `InsightResponse` đầy đủ field.
- Fingerprint stable giữa 2 lần generate cùng data → cached=True.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.models.entities import Category, InsightSnapshot, Transaction, User
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session, select


def _seed_data(engine: Engine, user_id: int) -> Category:
    """Seed dataset đủ điều kiện generate insight (>= 3 txns, >= 2 days,
    total >= 50k, range 30d xung quanh hôm nay)."""
    with Session(engine) as session:
        cat = Category(user_id=None, name="Ăn uống", is_system=True, color="#f00")
        session.add(cat)
        session.commit()
        session.refresh(cat)

        today = date.today()
        # 6 transactions trải 3 ngày trong 30 ngày qua, total 900k.
        for i in range(6):
            session.add(
                Transaction(
                    user_id=user_id,
                    category_id=cat.id,
                    merchant_name=f"M{i}",
                    amount=Decimal("150000"),
                    currency="VND",
                    transaction_date=today - timedelta(days=i % 3 + 1),
                ),
            )
        session.commit()
        return cat


class TestGenerate:
    def test_requires_auth(self, client: TestClient) -> None:
        response = client.post("/api/v1/insights/generate", json={})
        assert response.status_code == 401

    def test_generates_ready_with_data(
        self,
        client: TestClient,
        auth_user: User,
        engine: Engine,
    ) -> None:
        assert auth_user.id is not None
        _seed_data(engine, auth_user.id)

        response = client.post(
            "/api/v1/insights/generate",
            json={"range": "30d"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "ready"
        assert body["provider"] == "mock"
        assert body["cached"] is False
        assert "fingerprint" in body and len(body["fingerprint"]) == 64
        assert "payload" in body
        # Ít nhất 1 trong 3 sections có item (mock rules fire).
        payload = body["payload"]
        total_items = (
            len(payload["insights"])
            + len(payload["recommendations"])
            + len(payload["alerts"])
        )
        assert total_items >= 1

    def test_cache_hit_second_call(
        self,
        client: TestClient,
        auth_user: User,
        engine: Engine,
    ) -> None:
        assert auth_user.id is not None
        _seed_data(engine, auth_user.id)

        r1 = client.post("/api/v1/insights/generate", json={"range": "30d"})
        r2 = client.post("/api/v1/insights/generate", json={"range": "30d"})
        assert r1.status_code == 200
        assert r2.status_code == 200
        b1 = r1.json()
        b2 = r2.json()
        assert b1["fingerprint"] == b2["fingerprint"]
        assert b1["cached"] is False
        assert b2["cached"] is True
        assert b1["id"] == b2["id"]  # Cùng snapshot.

    def test_force_bypasses_cache(
        self,
        client: TestClient,
        auth_user: User,
        engine: Engine,
    ) -> None:
        assert auth_user.id is not None
        _seed_data(engine, auth_user.id)

        r1 = client.post("/api/v1/insights/generate", json={"range": "30d"})
        r2 = client.post(
            "/api/v1/insights/generate",
            json={"range": "30d", "force": True},
        )
        b1 = r1.json()
        b2 = r2.json()
        # Force tạo snapshot mới → khác id, cached=False.
        assert b2["cached"] is False
        assert b2["id"] != b1["id"]

    def test_insufficient_data(
        self,
        client: TestClient,
        auth_user: User,
    ) -> None:
        """Không seed transaction → insufficient_data."""
        response = client.post(
            "/api/v1/insights/generate",
            json={"range": "30d"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "insufficient_data"
        assert body["status_reason"] is not None
        assert body["payload"]["insights"] == []
        assert body["payload"]["recommendations"] == []
        assert body["payload"]["alerts"] == []

    def test_invalid_range_preset(
        self,
        client: TestClient,
        auth_user: User,  # noqa: ARG002
    ) -> None:
        response = client.post(
            "/api/v1/insights/generate",
            json={"range": "99d"},
        )
        # Pydantic validate → 422 (literal mismatch) hoặc 400 ở service.
        assert response.status_code in {400, 422}

    def test_custom_without_dates_fails(
        self,
        client: TestClient,
        auth_user: User,  # noqa: ARG002
    ) -> None:
        """Custom preset cần start_date+end_date, thiếu → 400."""
        response = client.post(
            "/api/v1/insights/generate",
            json={"range": "custom"},
        )
        assert response.status_code == 400

    def test_persists_snapshot(
        self,
        client: TestClient,
        auth_user: User,
        engine: Engine,
    ) -> None:
        """Snapshot phải được insert vào DB (audit trail)."""
        assert auth_user.id is not None
        _seed_data(engine, auth_user.id)

        client.post("/api/v1/insights/generate", json={"range": "30d"})

        with Session(engine) as session:
            rows = session.exec(
                select(InsightSnapshot).where(
                    InsightSnapshot.user_id == auth_user.id,
                ),
            ).all()
            assert len(rows) == 1
            assert rows[0].provider == "mock"
            assert rows[0].status == "ready"


class TestLatest:
    def test_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/insights/latest?range=30d")
        assert response.status_code == 401

    def test_404_when_empty(
        self,
        client: TestClient,
        auth_user: User,  # noqa: ARG002
    ) -> None:
        response = client.get("/api/v1/insights/latest?range=30d")
        assert response.status_code == 404

    def test_returns_latest_after_generate(
        self,
        client: TestClient,
        auth_user: User,
        engine: Engine,
    ) -> None:
        assert auth_user.id is not None
        _seed_data(engine, auth_user.id)
        client.post("/api/v1/insights/generate", json={"range": "30d"})

        response = client.get("/api/v1/insights/latest?range=30d")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert body["cached"] is True

    def test_isolates_by_range(
        self,
        client: TestClient,
        auth_user: User,
        engine: Engine,
    ) -> None:
        """/latest?range=7d không trả snapshot của 30d."""
        assert auth_user.id is not None
        _seed_data(engine, auth_user.id)
        client.post("/api/v1/insights/generate", json={"range": "30d"})

        response = client.get("/api/v1/insights/latest?range=7d")
        assert response.status_code == 404


class TestResponseSchema:
    def test_fields_present(
        self,
        client: TestClient,
        auth_user: User,
        engine: Engine,
    ) -> None:
        assert auth_user.id is not None
        _seed_data(engine, auth_user.id)

        response = client.post(
            "/api/v1/insights/generate",
            json={"range": "30d"},
        )
        body = response.json()
        # Field contract với frontend — đổi thì cập nhật types ở lib/insights-api.ts.
        for key in (
            "id",
            "range",
            "status",
            "status_reason",
            "provider",
            "fingerprint",
            "payload",
            "generated_at",
            "cached",
        ):
            assert key in body, f"missing key: {key}"
        for key in ("preset", "start", "end"):
            assert key in body["range"]
        for key in ("insights", "recommendations", "alerts"):
            assert key in body["payload"]
            assert isinstance(body["payload"][key], list)
