"""add merchants.updated_at column

Entity `Merchant` khai báo `updated_at` nhưng migration tạo bảng `merchants`
(`e5f6a7b8c9d0`) không tạo cột này → drift giữa entity và schema. Bổ sung cột
để khớp entity. Nối sau head thực tế `f2a3b4c5d6e7` (nhánh audit logs).

Revision ID: b7c8d9e0f1a2
Revises: f2a3b4c5d6e7
Create Date: 2026-05-29 19:45:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b7c8d9e0f1a2"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    if not _has_column("merchants", "updated_at"):
        op.add_column(
            "merchants",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )


def downgrade() -> None:
    op.drop_column("merchants", "updated_at")
