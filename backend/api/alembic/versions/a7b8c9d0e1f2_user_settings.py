"""add user_settings table

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-28
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("default_currency", sa.String(length=10), nullable=False, server_default="VND"),
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
            server_default="Asia/Ho_Chi_Minh",
        ),
        sa.Column("locale", sa.String(length=16), nullable=False, server_default="vi-VN"),
        sa.Column(
            "default_analytics_range",
            sa.String(length=20),
            nullable=False,
            server_default="30d",
        ),
        sa.Column("budget_month_start_day", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "number_format_locale",
            sa.String(length=16),
            nullable=False,
            server_default="vi-VN",
        ),
        sa.Column("show_decimals", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "allow_ai_data_processing",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "auto_generate_insights",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("assistant_use_history", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("receipt_file_retention_days", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("raw_prompt_retention_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_settings_user_id", "user_settings", ["user_id"], unique=True)

    op.execute(
        """
        INSERT INTO user_settings (
            user_id,
            default_currency,
            timezone,
            locale,
            number_format_locale
        )
        SELECT id, currency, timezone, locale, locale
        FROM users
        ON CONFLICT DO NOTHING
        """,
    )


def downgrade() -> None:
    op.drop_index("ix_user_settings_user_id", table_name="user_settings")
    op.drop_table("user_settings")
