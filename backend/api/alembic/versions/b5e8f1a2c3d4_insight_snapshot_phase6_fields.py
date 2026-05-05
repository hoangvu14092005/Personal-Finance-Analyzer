"""insight_snapshots add phase 6 fields (range_preset, provider, status, status_reason)

Revision ID: b5e8f1a2c3d4
Revises: a4b7c8d9e123
Create Date: 2026-05-05 11:30:00.000000

Thêm các cột Phase 6:
- `range_preset` để query "latest của user + preset" (7d/30d/this_month/...).
- `provider` để audit provider nào sinh payload (mock/ollama/gemini/...).
- `status` + `status_reason` cho fallback UI khi eligibility fail hoặc provider
  error (giữ snapshot thay vì throw 500, UI render thông báo an toàn).
- Index composite `(user_id, range_preset, created_at DESC)` để fetch latest
  nhanh không scan.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b5e8f1a2c3d4"
down_revision = "a4b7c8d9e123"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfill cho rows cũ (nếu có): default 'custom' preset + 'mock' provider
    # + 'ready' status → safe cho system đã prod.
    op.add_column(
        "insight_snapshots",
        sa.Column(
            "range_preset",
            sa.String(length=20),
            nullable=False,
            server_default="custom",
        ),
    )
    op.add_column(
        "insight_snapshots",
        sa.Column(
            "provider",
            sa.String(length=50),
            nullable=False,
            server_default="mock",
        ),
    )
    op.add_column(
        "insight_snapshots",
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="ready",
        ),
    )
    op.add_column(
        "insight_snapshots",
        sa.Column(
            "status_reason",
            sa.String(length=500),
            nullable=True,
        ),
    )

    # Index riêng cho range_preset để ORM query dùng.
    op.create_index(
        "ix_insight_snapshots_range_preset",
        "insight_snapshots",
        ["range_preset"],
        unique=False,
    )

    # Composite index cho hot path "latest by preset": ORDER BY created_at DESC
    # LIMIT 1 scan theo (user_id, range_preset) rồi pick latest.
    op.create_index(
        "ix_insight_snapshots_user_preset_created",
        "insight_snapshots",
        ["user_id", "range_preset", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_insight_snapshots_user_preset_created",
        table_name="insight_snapshots",
    )
    op.drop_index(
        "ix_insight_snapshots_range_preset",
        table_name="insight_snapshots",
    )
    op.drop_column("insight_snapshots", "status_reason")
    op.drop_column("insight_snapshots", "status")
    op.drop_column("insight_snapshots", "provider")
    op.drop_column("insight_snapshots", "range_preset")
