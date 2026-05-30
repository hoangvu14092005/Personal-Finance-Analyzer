"""create invoices and invoice_line_items tables

Trước đây hai bảng này chỉ được tạo bởi raw DDL `_ensure_tables()` lúc app
startup (đã bị loại bỏ — Alembic giờ là source of truth). Chuỗi migration cũ
thiếu bước tạo chúng, khiến `f6a7b8c9d0e1` (ALTER TABLE invoices ADD COLUMN
transaction_id) fail trên DB sạch. Migration này bổ sung bước tạo bảng, chèn
ngay trước `f6a7b8c9d0e1`.

Lưu ý: KHÔNG tạo cột `invoices.transaction_id` ở đây — cột đó do
`f6a7b8c9d0e1` thêm sau (giữ nguyên thứ tự lịch sử).

Revision ID: a0b1c2d3e4f5
Revises: e5f6a7b8c9d0
Create Date: 2026-05-29 19:30:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "a0b1c2d3e4f5"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def upgrade() -> None:
    # Idempotent guard: nếu bảng đã tồn tại (DB cũ từng chạy raw DDL),
    # bỏ qua tạo để không xung đột.
    if not _has_table("invoices"):
        op.create_table(
            "invoices",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("receipt_upload_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column(
                "invoice_number",
                sqlmodel.sql.sqltypes.AutoString(length=100),
                nullable=True,
            ),
            sa.Column(
                "template_symbol",
                sqlmodel.sql.sqltypes.AutoString(length=50),
                nullable=True,
            ),
            sa.Column("issue_date", sa.Date(), nullable=True),
            sa.Column(
                "tax_lookup_code",
                sqlmodel.sql.sqltypes.AutoString(length=100),
                nullable=True,
            ),
            sa.Column(
                "currency",
                sqlmodel.sql.sqltypes.AutoString(length=10),
                nullable=False,
                server_default="VND",
            ),
            sa.Column(
                "seller_name",
                sqlmodel.sql.sqltypes.AutoString(length=255),
                nullable=True,
            ),
            sa.Column(
                "seller_tax_id",
                sqlmodel.sql.sqltypes.AutoString(length=20),
                nullable=True,
            ),
            sa.Column(
                "seller_address",
                sqlmodel.sql.sqltypes.AutoString(length=500),
                nullable=True,
            ),
            sa.Column(
                "buyer_name",
                sqlmodel.sql.sqltypes.AutoString(length=255),
                nullable=True,
            ),
            sa.Column(
                "buyer_tax_id",
                sqlmodel.sql.sqltypes.AutoString(length=20),
                nullable=True,
            ),
            sa.Column(
                "buyer_address",
                sqlmodel.sql.sqltypes.AutoString(length=500),
                nullable=True,
            ),
            sa.Column(
                "payment_method",
                sqlmodel.sql.sqltypes.AutoString(length=100),
                nullable=True,
            ),
            sa.Column("subtotal_before_tax", sa.Numeric(15, 2), nullable=True),
            sa.Column("total_tax", sa.Numeric(15, 2), nullable=True),
            sa.Column("grand_total", sa.Numeric(15, 2), nullable=True),
            sa.Column(
                "amount_in_words",
                sqlmodel.sql.sqltypes.AutoString(length=500),
                nullable=True,
            ),
            sa.Column(
                "digital_signature",
                sqlmodel.sql.sqltypes.AutoString(length=500),
                nullable=True,
            ),
            sa.Column("signing_date", sa.Date(), nullable=True),
            sa.Column(
                "lookup_link",
                sqlmodel.sql.sqltypes.AutoString(length=500),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["receipt_upload_id"], ["receipt_uploads.id"], ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("receipt_upload_id"),
        )
        op.create_index("ix_invoices_receipt_upload_id", "invoices", ["receipt_upload_id"])
        op.create_index("ix_invoices_user_id", "invoices", ["user_id"])

    if not _has_table("invoice_line_items"):
        op.create_table(
            "invoice_line_items",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("invoice_id", sa.Integer(), nullable=False),
            sa.Column("line_number", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "item_name",
                sqlmodel.sql.sqltypes.AutoString(length=500),
                nullable=False,
            ),
            sa.Column("unit", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
            sa.Column(
                "quantity",
                sa.Numeric(10, 3),
                nullable=False,
                server_default="1",
            ),
            sa.Column("unit_price", sa.Numeric(15, 2), nullable=False),
            sa.Column("line_total", sa.Numeric(15, 2), nullable=False),
            sa.Column("vat_rate", sa.Numeric(5, 2), nullable=True),
            sa.Column("vat_amount", sa.Numeric(15, 2), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_invoice_line_items_invoice_id", "invoice_line_items", ["invoice_id"])


def downgrade() -> None:
    op.drop_index("ix_invoice_line_items_invoice_id", table_name="invoice_line_items")
    op.drop_table("invoice_line_items")
    op.drop_index("ix_invoices_user_id", table_name="invoices")
    op.drop_index("ix_invoices_receipt_upload_id", table_name="invoices")
    op.drop_table("invoices")
