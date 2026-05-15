from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ReceiptUploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_id: int
    status: str


class ReceiptStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_id: int
    file_name: str
    content_type: str
    status: str
    error_code: str | None
    error_message: str | None
    created_at: datetime


class OcrResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_id: int
    provider: str
    status: str
    raw_text: str | None
    confidence: float | None
    normalized_payload: str | None


class LineItemResponse(BaseModel):
    """Single line item from receipt."""
    model_config = ConfigDict(extra="forbid")

    id: int
    line_number: int
    item_name: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal
    category_id: int | None


class DraftReviewResponse(BaseModel):
    """Payload gộp cho trang OCR review (Phase 3.2).

    Frontend dùng response này để render form review draft với mọi field
    đã được parse sẵn (amount/currency/date/merchant) và category được suggest
    từ lịch sử user. Confidence kèm theo để UI highlight field nghi ngờ.
    """

    model_config = ConfigDict(extra="forbid")

    receipt_id: int
    receipt_status: str
    provider: str
    confidence: float | None
    merchant_name: str | None
    transaction_date: date | None
    amount: Decimal | None
    currency: str | None
    suggested_category_id: int | None
    raw_text: str | None
    line_items: list[LineItemResponse]


class InvoiceLineItemResponse(BaseModel):
    """Single line item from Vietnamese e-invoice with VAT info."""
    model_config = ConfigDict(extra="forbid")

    id: int
    line_number: int
    item_name: str
    unit: str | None
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    vat_rate: Decimal | None
    vat_amount: Decimal | None


class InvoiceResponse(BaseModel):
    """Full Vietnamese e-invoice response with nested line items."""
    model_config = ConfigDict(extra="forbid")

    id: int
    receipt_upload_id: int

    # Metadata
    invoice_number: str | None
    template_symbol: str | None
    issue_date: date | None
    tax_lookup_code: str | None
    currency: str

    # Seller
    seller_name: str | None
    seller_tax_id: str | None
    seller_address: str | None

    # Buyer
    buyer_name: str | None
    buyer_tax_id: str | None
    buyer_address: str | None
    payment_method: str | None

    # Totals
    subtotal_before_tax: Decimal | None
    total_tax: Decimal | None
    grand_total: Decimal | None
    amount_in_words: str | None

    # Authentication
    digital_signature: str | None
    signing_date: date | None
    lookup_link: str | None

    # Nested line items
    line_items: list[InvoiceLineItemResponse]
