"""Integration tests cho các chiều BI mới G2: products, tax, receipts-stats."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.models.entities import (
    Invoice,
    ReceiptLineItem,
    ReceiptUpload,
    Transaction,
    User,
)
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session


def _seed_confirmed_receipt_with_items(engine: Engine, user_id: int) -> None:
    """Seed 1 receipt đã confirm: transaction + line items + invoice (có VAT)."""
    with Session(engine) as session:
        receipt = ReceiptUpload(
            user_id=user_id,
            file_name="r.jpg",
            content_type="image/jpeg",
            file_size_bytes=10,
            storage_key=f"{user_id}/r.jpg",
            status="ready",
            ocr_status="succeeded",
            has_invoice=True,
        )
        session.add(receipt)
        session.commit()
        session.refresh(receipt)

        tx = Transaction(
            user_id=user_id,
            receipt_upload_id=receipt.id,
            merchant_name="Highlands Coffee",
            amount=Decimal("100000"),
            currency="VND",
            transaction_date=date(2026, 5, 18),
            source="invoice",
            status="confirmed",
        )
        session.add(tx)
        session.commit()
        session.refresh(tx)

        # Line items đã gắn transaction (đã confirm).
        session.add_all([
            ReceiptLineItem(
                user_id=user_id,
                receipt_upload_id=receipt.id,
                transaction_id=tx.id,
                line_number=0,
                item_name="Cà phê sữa đá",
                quantity=Decimal("2"),
                unit_price=Decimal("25000"),
                total_price=Decimal("50000"),
            ),
            ReceiptLineItem(
                user_id=user_id,
                receipt_upload_id=receipt.id,
                transaction_id=tx.id,
                line_number=1,
                item_name="Bánh mì",
                quantity=Decimal("1"),
                unit_price=Decimal("50000"),
                total_price=Decimal("50000"),
            ),
        ])
        # Invoice đã gắn transaction.
        session.add(
            Invoice(
                receipt_upload_id=receipt.id,
                user_id=user_id,
                transaction_id=tx.id,
                invoice_number="INV-1",
                seller_name="Highlands Coffee",
                seller_tax_id="0301234567",
                currency="VND",
                subtotal_before_tax=Decimal("100000"),
                total_tax=Decimal("10000"),
                grand_total=Decimal("110000"),
                issue_date=date(2026, 5, 18),
            ),
        )
        session.commit()


def _seed_unconfirmed_receipt(engine: Engine, user_id: int) -> None:
    """Receipt OCR xong nhưng CHƯA confirm — không được vào BI products/tax."""
    with Session(engine) as session:
        receipt = ReceiptUpload(
            user_id=user_id,
            file_name="u.jpg",
            content_type="image/jpeg",
            file_size_bytes=10,
            storage_key=f"{user_id}/u.jpg",
            status="ready",
            ocr_status="succeeded",
            has_invoice=True,
        )
        session.add(receipt)
        session.commit()
        session.refresh(receipt)
        # Line item KHÔNG có transaction_id (chưa confirm).
        session.add(
            ReceiptLineItem(
                user_id=user_id,
                receipt_upload_id=receipt.id,
                transaction_id=None,
                line_number=0,
                item_name="Sản phẩm nháp",
                quantity=Decimal("1"),
                unit_price=Decimal("999000"),
                total_price=Decimal("999000"),
            ),
        )
        session.commit()


class TestAnalyticsProducts:
    def test_requires_auth(self, client: TestClient) -> None:
        assert client.get("/api/v1/analytics/products").status_code == 401

    def test_top_products_from_confirmed_only(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        _seed_confirmed_receipt_with_items(engine, auth_user.id)
        _seed_unconfirmed_receipt(engine, auth_user.id)

        resp = client.get(
            "/api/v1/analytics/products"
            "?range=custom&start_date=2026-05-01&end_date=2026-05-31",
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        names = {i["item_name"] for i in items}
        # Chỉ line items đã confirm xuất hiện; "sản phẩm nháp" bị loại.
        assert "cà phê sữa đá" in names
        assert "bánh mì" in names
        assert all("nháp" not in n for n in names)


class TestAnalyticsTax:
    def test_vat_totals_and_sellers(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        _seed_confirmed_receipt_with_items(engine, auth_user.id)

        resp = client.get(
            "/api/v1/analytics/tax"
            "?range=custom&start_date=2026-05-01&end_date=2026-05-31",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert Decimal(body["total_tax"]) == Decimal("10000")
        assert Decimal(body["subtotal_before_tax"]) == Decimal("100000")
        assert body["invoice_count"] == 1
        assert body["effective_tax_rate"] == 10.0
        assert body["top_sellers"][0]["seller_name"] == "Highlands Coffee"
        assert body["top_sellers"][0]["seller_tax_id"] == "0301234567"


class TestAnalyticsReceiptStats:
    def test_receipt_pipeline_stats(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        assert auth_user.id is not None
        _seed_confirmed_receipt_with_items(engine, auth_user.id)
        _seed_unconfirmed_receipt(engine, auth_user.id)

        # Range rộng theo created_at (hôm nay) — dùng 12m để chắc chắn bao trùm.
        resp = client.get("/api/v1/analytics/receipts-stats?range=12m")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_receipts"] == 2
        assert body["ready_count"] == 2
        assert body["with_invoice_count"] == 2
        assert body["confirmed_count"] == 1
        assert body["ocr_success_rate"] == 100.0
