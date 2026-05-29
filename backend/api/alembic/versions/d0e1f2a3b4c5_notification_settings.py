"""add notification settings

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-05-29
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column("email_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "user_settings",
        sa.Column("push_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "user_settings",
        sa.Column("budget_alerts_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "user_settings",
        sa.Column("receipt_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "user_settings",
        sa.Column("insight_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "insight_notifications_enabled")
    op.drop_column("user_settings", "receipt_notifications_enabled")
    op.drop_column("user_settings", "budget_alerts_enabled")
    op.drop_column("user_settings", "push_notifications_enabled")
    op.drop_column("user_settings", "email_notifications_enabled")
