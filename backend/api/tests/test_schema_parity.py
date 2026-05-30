"""Bug 1 — Alembic là source of truth cho schema.

- `_ensure_tables()` raw DDL đã bị xóa khỏi `app.main` (không còn nguồn drift).
- Bảng `invoices` sinh từ entity (SQLModel.metadata) có cột `transaction_id`,
  nhất quán với migration `f6a7b8c9d0e1`.
"""
from __future__ import annotations

import app.main as main_module
from app.models.entities import Invoice

# Các cột Alembic kỳ vọng cho bảng invoices (gồm transaction_id thêm ở
# migration f6a7b8c9d0e1_receipt_retrieval_and_confirm_flow).
EXPECTED_INVOICE_COLUMNS = {
    "id",
    "receipt_upload_id",
    "user_id",
    "transaction_id",
    "invoice_number",
    "template_symbol",
    "issue_date",
    "tax_lookup_code",
    "currency",
    "seller_name",
    "seller_tax_id",
    "seller_address",
    "buyer_name",
    "buyer_tax_id",
    "buyer_address",
    "payment_method",
    "subtotal_before_tax",
    "total_tax",
    "grand_total",
    "amount_in_words",
    "digital_signature",
    "signing_date",
    "lookup_link",
    "created_at",
}


def test_ensure_tables_removed() -> None:
    """Raw DDL startup path bị xóa — Alembic là nguồn schema duy nhất."""
    assert not hasattr(main_module, "_ensure_tables")


def test_invoice_entity_has_transaction_id() -> None:
    columns = set(Invoice.__table__.columns.keys())
    assert "transaction_id" in columns


def test_invoice_columns_superset_of_alembic_expected() -> None:
    columns = set(Invoice.__table__.columns.keys())
    missing = EXPECTED_INVOICE_COLUMNS - columns
    assert not missing, f"Entity invoices thiếu cột: {missing}"
