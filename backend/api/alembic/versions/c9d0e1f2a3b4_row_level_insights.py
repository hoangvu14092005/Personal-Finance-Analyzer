"""add row-level insights

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-05-29
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "insights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="info"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column("evidence_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("actions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("range_start", sa.Date(), nullable=False),
        sa.Column("range_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_insights_user_id", "insights", ["user_id"], unique=False)
    op.create_index("ix_insights_type", "insights", ["type"], unique=False)
    op.create_index("ix_insights_severity", "insights", ["severity"], unique=False)
    op.create_index("ix_insights_status", "insights", ["status"], unique=False)
    op.create_index("ix_insights_range_start", "insights", ["range_start"], unique=False)
    op.create_index("ix_insights_range_end", "insights", ["range_end"], unique=False)
    op.create_index(
        "ix_insights_user_status_created",
        "insights",
        ["user_id", "status", "created_at"],
        unique=False,
    )

    op.create_table(
        "insight_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("insight_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.String(length=20), nullable=False),
        sa.Column("comment", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["insight_id"], ["insights.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_insight_feedback_insight_id",
        "insight_feedback",
        ["insight_id"],
        unique=False,
    )
    op.create_index(
        "ix_insight_feedback_user_id",
        "insight_feedback",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_insight_feedback_user_id", table_name="insight_feedback")
    op.drop_index("ix_insight_feedback_insight_id", table_name="insight_feedback")
    op.drop_table("insight_feedback")
    op.drop_index("ix_insights_user_status_created", table_name="insights")
    op.drop_index("ix_insights_range_end", table_name="insights")
    op.drop_index("ix_insights_range_start", table_name="insights")
    op.drop_index("ix_insights_status", table_name="insights")
    op.drop_index("ix_insights_severity", table_name="insights")
    op.drop_index("ix_insights_type", table_name="insights")
    op.drop_index("ix_insights_user_id", table_name="insights")
    op.drop_table("insights")
