"""add user profile defaults

Revision ID: f2a1bb149083
Revises: c9702a06526e
Create Date: 2026-03-30 13:56:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = "f2a1bb149083"
down_revision = "c9702a06526e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "currency",
            sqlmodel.sql.sqltypes.AutoString(length=10),
            nullable=False,
            server_default="VND",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "timezone",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=False,
            server_default="Asia/Ho_Chi_Minh",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "locale",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=False,
            server_default="vi-VN",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "locale")
    op.drop_column("users", "timezone")
    op.drop_column("users", "currency")
