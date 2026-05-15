"""add receipt_line_items table

Revision ID: d3e4f5a6b7c8
Revises: c1d2e3f4a5b6
Create Date: 2026-05-14
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "d3e4f5a6b7c8"
down_revision = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "receipt_line_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("receipt_upload_id", sa.Integer(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("item_name", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["receipt_upload_id"],
            ["receipt_uploads.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_receipt_line_items_receipt",
        "receipt_line_items",
        ["receipt_upload_id"],
        unique=False,
    )
    op.create_index(
        "ix_receipt_line_items_category",
        "receipt_line_items",
        ["category_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_receipt_line_items_category", table_name="receipt_line_items")
    op.drop_index("ix_receipt_line_items_receipt", table_name="receipt_line_items")
    op.drop_table("receipt_line_items")
