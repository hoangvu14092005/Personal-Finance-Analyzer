"""Tests for merchant search APIs."""
from __future__ import annotations

from app.models.entities import Merchant, User, UserMerchantAlias
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session


def _seed_merchant(session: Session, *, display_name: str, normalized_name: str) -> Merchant:
    merchant = Merchant(display_name=display_name, normalized_name=normalized_name)
    session.add(merchant)
    session.commit()
    session.refresh(merchant)
    assert merchant.id is not None
    return merchant


class TestMerchantSearchAuth:
    def test_search_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/merchants/search", params={"q": "high"})
        assert response.status_code == 401


class TestMerchantSearch:
    def test_search_returns_user_alias_first(
        self,
        client: TestClient,
        auth_user: User,
        db_session: Session,
    ) -> None:
        assert auth_user.id is not None
        merchant = _seed_merchant(
            db_session,
            display_name="Highlands Coffee",
            normalized_name="highlands coffee",
        )
        alias = UserMerchantAlias(
            user_id=auth_user.id,
            raw_name="Highlands Nguyen Hue",
            normalized_name="highlands nguyen hue",
            merchant_id=merchant.id or 0,
            category_id=7,
            confidence=0.91,
            source="ocr",
        )
        db_session.add(alias)
        db_session.commit()

        response = client.get("/api/v1/merchants/search", params={"q": "highlands"})

        assert response.status_code == 200
        body = response.json()
        assert body["items"][0]["match_type"] == "alias"
        assert body["items"][0]["display_name"] == "Highlands Coffee"
        assert body["items"][0]["raw_name"] == "Highlands Nguyen Hue"
        assert body["items"][0]["category_id"] == 7

    def test_search_does_not_return_other_user_alias_metadata(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        with Session(engine) as session:
            merchant = _seed_merchant(
                session,
                display_name="Grab",
                normalized_name="grab",
            )
            other = User(email="merchant-other@example.com", password_hash="x")
            session.add(other)
            session.commit()
            session.refresh(other)
            assert other.id is not None
            session.add(
                UserMerchantAlias(
                    user_id=other.id,
                    raw_name="Grab Secret Alias",
                    normalized_name="grab secret alias",
                    merchant_id=merchant.id or 0,
                    category_id=99,
                    source="manual",
                ),
            )
            session.commit()

        response = client.get("/api/v1/merchants/search", params={"q": "grab"})

        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["match_type"] == "merchant"
        assert body["items"][0]["raw_name"] is None
        assert body["items"][0]["category_id"] is None
