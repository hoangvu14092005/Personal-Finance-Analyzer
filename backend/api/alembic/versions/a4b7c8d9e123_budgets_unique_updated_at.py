"""budgets unique constraint + updated_at (Phase 5.1)

Revision ID: a4b7c8d9e123
Revises: 8ae8dfe4de39
Create Date: 2026-05-03 21:40:00.000000

Thêm:
- `updated_at` cho bảng `budgets` (NOT NULL, default now, onupdate now).
- UniqueConstraint (user_id, category_id, period_month) — tránh duplicate
  khi user set budget 2 lần cho cùng category trong cùng tháng.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a4b7c8d9e123"
down_revision = "8ae8dfe4de39"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. updated_at — backfill server_default=now() cho rows hiện có.
    op.add_column(
        "budgets",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 2. Unique constraint trên (user_id, category_id, period_month).
    op.create_unique_constraint(
        "uq_budgets_user_category_period",
        "budgets",
        ["user_id", "category_id", "period_month"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_budgets_user_category_period",
        "budgets",
        type_="unique",
    )
    op.drop_column("budgets", "updated_at")
