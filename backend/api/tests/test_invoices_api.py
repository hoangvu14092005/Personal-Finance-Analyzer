"""Tests for direct Invoice retrieval APIs."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.models.entities import Invoice, InvoiceLineItem, ReceiptUpload, User
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session


def _seed_invoice(session: Session, *, user_id: int) -> Invoice:
    receipt = ReceiptUpload(
        user_id=user_id,
        file_name="vat-invoice.pdf",
        content_type="application/pdf",
        file_size_bytes=2048,
        storage_key="receipts/vat-invoice.pdf",
        merchant_name="Công ty Cafe Việt",
        receipt_date=date(2026, 5, 20),
        total_amount=Decimal("110000"),
        currency="VND",
        status="ready",
        ocr_status="ready",
        has_invoice=True,
    )
    session.add(receipt)
    session.commit()
    session.refresh(receipt)
    assert receipt.id is not None

    invoice = Invoice(
        user_id=user_id,
        receipt_upload_id=receipt.id,
        invoice_number="INV-2026-0001",
        template_symbol="1C25TAA",
        issue_date=date(2026, 5, 20),
        tax_lookup_code="ABC123",
        currency="VND",
        seller_name="Công ty Cafe Việt",
        seller_tax_id="0101234567",
        buyer_name="Nguyễn Văn A",
        buyer_tax_id="0312345678",
        payment_method="Chuyển khoản",
        subtotal_before_tax=Decimal("100000"),
        total_tax=Decimal("10000"),
        grand_total=Decimal("110000"),
        lookup_link="https://invoice.example/lookup/ABC123",
    )
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    assert invoice.id is not None

    session.add_all(
        [
            InvoiceLineItem(
                invoice_id=invoice.id,
                line_number=2,
                item_name="Bánh ngọt",
                unit="cái",
                quantity=Decimal("1"),
                unit_price=Decimal("30000"),
                line_total=Decimal("30000"),
                vat_rate=Decimal("10"),
                vat_amount=Decimal("3000"),
            ),
            InvoiceLineItem(
                invoice_id=invoice.id,
                line_number=1,
                item_name="Cà phê",
                unit="ly",
                quantity=Decimal("2"),
                unit_price=Decimal("35000"),
                line_total=Decimal("70000"),
                vat_rate=Decimal("10"),
                vat_amount=Decimal("7000"),
            ),
        ],
    )
    session.commit()
    return invoice


class TestInvoicesAuth:
    def test_detail_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/invoices/1")
        assert response.status_code == 401


class TestInvoiceRetrieval:
    def test_get_invoice_returns_detail_with_ordered_line_items(
        self,
        client: TestClient,
        auth_user: User,
        db_session: Session,
    ) -> None:
        assert auth_user.id is not None
        invoice = _seed_invoice(db_session, user_id=auth_user.id)

        response = client.get(f"/api/v1/invoices/{invoice.id}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == invoice.id
        assert body["invoice_number"] == "INV-2026-0001"
        assert body["seller_tax_id"] == "0101234567"
        assert Decimal(body["grand_total"]) == Decimal("110000")
        assert [item["line_number"] for item in body["line_items"]] == [1, 2]
        assert body["line_items"][0]["item_name"] == "Cà phê"

    def test_get_invoice_line_items_returns_rows_only(
        self,
        client: TestClient,
        auth_user: User,
        db_session: Session,
    ) -> None:
        assert auth_user.id is not None
        invoice = _seed_invoice(db_session, user_id=auth_user.id)

        response = client.get(f"/api/v1/invoices/{invoice.id}/line-items")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert [item["item_name"] for item in body] == ["Cà phê", "Bánh ngọt"]
        assert Decimal(body[0]["line_total"]) == Decimal("70000")

    def test_invoice_detail_respects_ownership(
        self,
        engine: Engine,
        client: TestClient,
        auth_user: User,
    ) -> None:
        with Session(engine) as session:
            other = User(email="invoice-owner@example.com", password_hash="x")
            session.add(other)
            session.commit()
            session.refresh(other)
            assert other.id is not None
            invoice = _seed_invoice(session, user_id=other.id)
            invoice_id = invoice.id

        response = client.get(f"/api/v1/invoices/{invoice_id}")
        line_items_response = client.get(f"/api/v1/invoices/{invoice_id}/line-items")

        assert response.status_code == 404
        assert line_items_response.status_code == 404
