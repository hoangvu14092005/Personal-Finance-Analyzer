"""receipt retrieval and confirm flow

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-28 16:20:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("receipt_uploads", sa.Column("merchant_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True))
    op.add_column("receipt_uploads", sa.Column("receipt_date", sa.Date(), nullable=True))
    op.add_column("receipt_uploads", sa.Column("total_amount", sa.Numeric(15, 2), nullable=True))
    op.add_column("receipt_uploads", sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True))
    op.add_column("receipt_uploads", sa.Column("ocr_status", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False, server_default="pending"))
    op.add_column("receipt_uploads", sa.Column("has_invoice", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("receipt_uploads", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_receipt_uploads_merchant_name", "receipt_uploads", ["merchant_name"])
    op.create_index("ix_receipt_uploads_receipt_date", "receipt_uploads", ["receipt_date"])
    op.create_index("ix_receipt_uploads_ocr_status", "receipt_uploads", ["ocr_status"])
    op.create_index("ix_receipt_uploads_has_invoice", "receipt_uploads", ["has_invoice"])

    op.add_column("transactions", sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False, server_default="confirmed"))
    op.add_column("transactions", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_transactions_status", "transactions", ["status"])
    op.create_index(
        "uq_transactions_user_receipt_active",
        "transactions",
        ["user_id", "receipt_upload_id"],
        unique=True,
        postgresql_where=sa.text("receipt_upload_id IS NOT NULL"),
    )

    op.add_column("invoices", sa.Column("transaction_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_invoices_transaction_id_transactions", "invoices", "transactions", ["transaction_id"], ["id"])
    op.create_index("ix_invoices_transaction_id", "invoices", ["transaction_id"])

    op.add_column("receipt_line_items", sa.Column("user_id", sa.Integer(), nullable=True))
    op.add_column("receipt_line_items", sa.Column("transaction_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_receipt_line_items_user_id_users", "receipt_line_items", "users", ["user_id"], ["id"])
    op.create_foreign_key("fk_receipt_line_items_transaction_id_transactions", "receipt_line_items", "transactions", ["transaction_id"], ["id"])
    op.create_index("ix_receipt_line_items_user_id", "receipt_line_items", ["user_id"])
    op.create_index("ix_receipt_line_items_transaction_id", "receipt_line_items", ["transaction_id"])


def downgrade() -> None:
    op.drop_index("ix_receipt_line_items_transaction_id", table_name="receipt_line_items")
    op.drop_index("ix_receipt_line_items_user_id", table_name="receipt_line_items")
    op.drop_constraint("fk_receipt_line_items_transaction_id_transactions", "receipt_line_items", type_="foreignkey")
    op.drop_constraint("fk_receipt_line_items_user_id_users", "receipt_line_items", type_="foreignkey")
    op.drop_column("receipt_line_items", "transaction_id")
    op.drop_column("receipt_line_items", "user_id")

    op.drop_index("ix_invoices_transaction_id", table_name="invoices")
    op.drop_constraint("fk_invoices_transaction_id_transactions", "invoices", type_="foreignkey")
    op.drop_column("invoices", "transaction_id")

    op.drop_index("uq_transactions_user_receipt_active", table_name="transactions")
    op.drop_index("ix_transactions_status", table_name="transactions")
    op.drop_column("transactions", "confirmed_at")
    op.drop_column("transactions", "status")

    op.drop_index("ix_receipt_uploads_has_invoice", table_name="receipt_uploads")
    op.drop_index("ix_receipt_uploads_ocr_status", table_name="receipt_uploads")
    op.drop_index("ix_receipt_uploads_receipt_date", table_name="receipt_uploads")
    op.drop_index("ix_receipt_uploads_merchant_name", table_name="receipt_uploads")
    op.drop_column("receipt_uploads", "updated_at")
    op.drop_column("receipt_uploads", "has_invoice")
    op.drop_column("receipt_uploads", "ocr_status")
    op.drop_column("receipt_uploads", "currency")
    op.drop_column("receipt_uploads", "total_amount")
    op.drop_column("receipt_uploads", "receipt_date")
    op.drop_column("receipt_uploads", "merchant_name")
