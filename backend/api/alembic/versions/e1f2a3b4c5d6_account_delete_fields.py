"""add account delete request fields

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-05-29
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("account_deletion_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("account_deletion_scheduled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("account_deletion_cancelled_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "account_deletion_cancelled_at")
    op.drop_column("users", "account_deletion_scheduled_at")
    op.drop_column("users", "account_deletion_requested_at")
