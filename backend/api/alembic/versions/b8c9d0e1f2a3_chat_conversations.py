"""add chat conversations

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-05-29
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index(
        "ix_chat_conversations_user_id",
        "chat_conversations",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_chat_conversations_user_updated",
        "chat_conversations",
        ["user_id", "updated_at"],
        unique=False,
    )

    op.add_column("chat_messages", sa.Column("conversation_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_chat_messages_conversation_id_chat_conversations",
        "chat_messages",
        "chat_conversations",
        ["conversation_id"],
        ["id"],
    )
    op.create_index(
        "ix_chat_messages_conversation_id",
        "chat_messages",
        ["conversation_id"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO chat_conversations (user_id, title, created_at, updated_at)
        SELECT
            user_id,
            'Lịch sử chat',
            MIN(created_at),
            MAX(created_at)
        FROM chat_messages
        GROUP BY user_id
        """,
    )
    op.execute(
        """
        UPDATE chat_messages AS msg
        SET conversation_id = conv.id
        FROM chat_conversations AS conv
        WHERE msg.conversation_id IS NULL
          AND conv.user_id = msg.user_id
          AND conv.title = 'Lịch sử chat'
        """,
    )


def downgrade() -> None:
    op.drop_index("ix_chat_messages_conversation_id", table_name="chat_messages")
    op.drop_constraint(
        "fk_chat_messages_conversation_id_chat_conversations",
        "chat_messages",
        type_="foreignkey",
    )
    op.drop_column("chat_messages", "conversation_id")
    op.drop_index("ix_chat_conversations_user_updated", table_name="chat_conversations")
    op.drop_index("ix_chat_conversations_user_id", table_name="chat_conversations")
    op.drop_table("chat_conversations")
