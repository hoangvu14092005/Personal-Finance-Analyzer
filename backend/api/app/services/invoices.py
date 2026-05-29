"""Invoice retrieval service.

Invoices are document/evidence records. These helpers only retrieve invoice
metadata and line items; they do not participate in financial totals.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.entities import Invoice, InvoiceLineItem, ReceiptUpload
from app.schemas.receipts import InvoiceLineItemResponse, InvoiceResponse


def ensure_invoice_owner(session: Session, *, invoice_id: int, user_id: int) -> Invoice:
    invoice = session.get(Invoice, invoice_id)
    if invoice is None or invoice.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    receipt = session.get(ReceiptUpload, invoice.receipt_upload_id)
    if receipt is None or receipt.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


def invoice_line_item_response(item: InvoiceLineItem) -> InvoiceLineItemResponse:
    return InvoiceLineItemResponse(
        id=item.id or 0,
        line_number=item.line_number,
        item_name=item.item_name,
        unit=item.unit,
        quantity=item.quantity,
        unit_price=item.unit_price,
        line_total=item.line_total,
        vat_rate=item.vat_rate,
        vat_amount=item.vat_amount,
    )


def list_invoice_line_items(
    session: Session,
    *,
    invoice_id: int,
    user_id: int,
) -> list[InvoiceLineItemResponse]:
    invoice = ensure_invoice_owner(session, invoice_id=invoice_id, user_id=user_id)
    rows = session.exec(
        select(InvoiceLineItem)
        .where(InvoiceLineItem.invoice_id == invoice.id)
        .order_by(InvoiceLineItem.line_number),
    ).all()
    return [invoice_line_item_response(item) for item in rows]


def invoice_detail_response(session: Session, *, invoice_id: int, user_id: int) -> InvoiceResponse:
    invoice = ensure_invoice_owner(session, invoice_id=invoice_id, user_id=user_id)
    line_items = list_invoice_line_items(session, invoice_id=invoice_id, user_id=user_id)
    return InvoiceResponse(
        id=invoice.id or 0,
        receipt_upload_id=invoice.receipt_upload_id,
        invoice_number=invoice.invoice_number,
        template_symbol=invoice.template_symbol,
        issue_date=invoice.issue_date,
        tax_lookup_code=invoice.tax_lookup_code,
        currency=invoice.currency,
        seller_name=invoice.seller_name,
        seller_tax_id=invoice.seller_tax_id,
        seller_address=invoice.seller_address,
        buyer_name=invoice.buyer_name,
        buyer_tax_id=invoice.buyer_tax_id,
        buyer_address=invoice.buyer_address,
        payment_method=invoice.payment_method,
        subtotal_before_tax=invoice.subtotal_before_tax,
        total_tax=invoice.total_tax,
        grand_total=invoice.grand_total,
        amount_in_words=invoice.amount_in_words,
        digital_signature=invoice.digital_signature,
        signing_date=invoice.signing_date,
        lookup_link=invoice.lookup_link,
        line_items=line_items,
    )


__all__ = [
    "ensure_invoice_owner",
    "invoice_detail_response",
    "invoice_line_item_response",
    "list_invoice_line_items",
]
