"""extend receipt upload metadata

Revision ID: 8ae8dfe4de39
Revises: f2a1bb149083
Create Date: 2026-03-30 15:30:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = "8ae8dfe4de39"
down_revision = "f2a1bb149083"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "receipt_uploads",
        sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "receipt_uploads",
        sa.Column("error_code", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
    )
    op.add_column(
        "receipt_uploads",
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("receipt_uploads", "error_message")
    op.drop_column("receipt_uploads", "error_code")
    op.drop_column("receipt_uploads", "file_size_bytes")
