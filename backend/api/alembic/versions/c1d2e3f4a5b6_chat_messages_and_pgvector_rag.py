"""chat_messages + pgvector + receipt_text_chunks + transactions.search_embedding (Phase 6 + 7)

Combined migration cho:
- Phase 6: table chat_messages (chatbot conversation history)
- Phase 7: enable pgvector, table receipt_text_chunks, column transactions.search_embedding

Revision ID: c1d2e3f4a5b6
Revises: b5e8f1a2c3d4
Create Date: 2026-05-13
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers
revision = "c1d2e3f4a5b6"
down_revision = "b5e8f1a2c3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIMENSION = 384


def upgrade() -> None:
    # Phase 6: chat_messages table
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("tool_calls_json", sa.Text(), nullable=True),
        sa.Column("tool_call_id", sa.String(length=100), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_messages_user_id",
        "chat_messages",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_chat_messages_user_created",
        "chat_messages",
        ["user_id", "created_at"],
        unique=False,
    )

    # Phase 7: enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Phase 7: receipt_text_chunks table
    op.create_table(
        "receipt_text_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("receipt_upload_id", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=False),
        sa.Column(
            "source_type", sa.String(length=32), nullable=False,
            server_default="receipt_ocr",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["receipt_upload_id"],
            ["receipt_uploads.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_receipt_text_chunks_user_id",
        "receipt_text_chunks",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_receipt_text_chunks_receipt",
        "receipt_text_chunks",
        ["receipt_upload_id"],
        unique=False,
    )
    # IVFFlat index cho cosine similarity search.
    # lists=50 phù hợp với dataset nhỏ (< 100k rows). Tune lại khi scale.
    op.execute(
        "CREATE INDEX ix_receipt_text_chunks_embedding "
        "ON receipt_text_chunks USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 50)",
    )

    # Phase 7: thêm search_embedding column vào transactions
    op.add_column(
        "transactions",
        sa.Column("search_embedding", Vector(EMBEDDING_DIMENSION), nullable=True),
    )
    op.execute(
        "CREATE INDEX ix_transactions_search_embedding "
        "ON transactions USING ivfflat (search_embedding vector_cosine_ops) "
        "WITH (lists = 50) "
        "WHERE search_embedding IS NOT NULL",
    )


def downgrade() -> None:
    # Reverse order: drop indexes + columns first, then tables, then extension
    op.execute("DROP INDEX IF EXISTS ix_transactions_search_embedding")
    op.drop_column("transactions", "search_embedding")

    op.execute("DROP INDEX IF EXISTS ix_receipt_text_chunks_embedding")
    op.drop_index("ix_receipt_text_chunks_receipt", table_name="receipt_text_chunks")
    op.drop_index("ix_receipt_text_chunks_user_id", table_name="receipt_text_chunks")
    op.drop_table("receipt_text_chunks")

    op.drop_index("ix_chat_messages_user_created", table_name="chat_messages")
    op.drop_index("ix_chat_messages_user_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    # Không drop extension vì có thể có table khác dùng (defensive)
    # User có thể manual drop: DROP EXTENSION vector CASCADE
