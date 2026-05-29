"""merchants and user merchant aliases

Revision ID: e5f6a7b8c9d0
Revises: d3e4f5a6b7c8
Create Date: 2026-05-28
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "e5f6a7b8c9d0"
down_revision = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _normalized_sql(column: str, dialect_name: str) -> str:
    if dialect_name == "postgresql":
        return f"lower(regexp_replace(trim({column}), '\\s+', ' ', 'g'))"
    return f"lower(trim({column}))"


def upgrade() -> None:
    op.create_table(
        "merchants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_name", name="uq_merchants_normalized_name"),
    )
    op.create_index("ix_merchants_normalized_name", "merchants", ["normalized_name"])

    op.create_table(
        "user_merchant_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("raw_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("merchant_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "raw_name", name="uq_user_merchant_aliases_user_raw"),
    )
    op.create_index("ix_user_merchant_aliases_user_id", "user_merchant_aliases", ["user_id"])
    op.create_index("ix_user_merchant_aliases_raw_name", "user_merchant_aliases", ["raw_name"])
    op.create_index(
        "ix_user_merchant_aliases_normalized_name",
        "user_merchant_aliases",
        ["normalized_name"],
    )
    op.create_index(
        "ix_user_merchant_aliases_merchant_id",
        "user_merchant_aliases",
        ["merchant_id"],
    )
    op.create_index(
        "ix_user_merchant_aliases_category_id",
        "user_merchant_aliases",
        ["category_id"],
    )

    op.add_column("transactions", sa.Column("merchant_id", sa.Integer(), nullable=True))
    op.add_column(
        "transactions",
        sa.Column("raw_merchant_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
    )
    op.add_column(
        "transactions",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_transactions_merchant_id_merchants",
        "transactions",
        "merchants",
        ["merchant_id"],
        ["id"],
    )
    op.create_index("ix_transactions_merchant_id", "transactions", ["merchant_id"])
    op.create_index("ix_transactions_user_date", "transactions", ["user_id", "transaction_date"])
    op.create_index(
        "ix_transactions_user_category_date",
        "transactions",
        ["user_id", "category_id", "transaction_date"],
    )
    op.create_index("ix_transactions_user_merchant", "transactions", ["user_id", "merchant_id"])

    bind = op.get_bind()
    dialect_name = bind.dialect.name
    normalized_tx = _normalized_sql("merchant_name", dialect_name)
    normalized_mapping = _normalized_sql("raw_merchant_name", dialect_name)

    op.execute("UPDATE transactions SET raw_merchant_name = merchant_name WHERE merchant_name IS NOT NULL")
    op.execute(
        sa.text(
            f"""
            INSERT INTO merchants (normalized_name, display_name)
            SELECT normalized_name, MIN(display_name) AS display_name
            FROM (
                SELECT {normalized_tx} AS normalized_name, trim(merchant_name) AS display_name
                FROM transactions
                WHERE merchant_name IS NOT NULL AND trim(merchant_name) <> ''
                UNION ALL
                SELECT {normalized_mapping} AS normalized_name, trim(raw_merchant_name) AS display_name
                FROM user_merchant_mappings
                WHERE raw_merchant_name IS NOT NULL AND trim(raw_merchant_name) <> ''
            ) merchant_source
            GROUP BY normalized_name
            """,
        ),
    )

    op.execute(
        sa.text(
            f"""
            UPDATE transactions
            SET merchant_id = merchants.id
            FROM merchants
            WHERE transactions.merchant_name IS NOT NULL
              AND {normalized_tx} = merchants.normalized_name
            """,
        ),
    )

    op.execute(
        sa.text(
            f"""
            INSERT INTO user_merchant_aliases
                (user_id, raw_name, normalized_name, merchant_id, category_id, confidence, source)
            SELECT DISTINCT ON (m.user_id, trim(m.raw_merchant_name))
                m.user_id,
                trim(m.raw_merchant_name),
                {normalized_mapping},
                merchants.id,
                m.category_id,
                m.confidence,
                'manual'
            FROM user_merchant_mappings m
            JOIN merchants ON merchants.normalized_name = {normalized_mapping}
            WHERE trim(m.raw_merchant_name) <> ''
            """
            if dialect_name == "postgresql"
            else f"""
            INSERT OR IGNORE INTO user_merchant_aliases
                (user_id, raw_name, normalized_name, merchant_id, category_id, confidence, source)
            SELECT
                m.user_id,
                trim(m.raw_merchant_name),
                {normalized_mapping},
                merchants.id,
                m.category_id,
                m.confidence,
                'manual'
            FROM user_merchant_mappings m
            JOIN merchants ON merchants.normalized_name = {normalized_mapping}
            WHERE trim(m.raw_merchant_name) <> ''
            """,
        ),
    )

    if dialect_name == "postgresql":
        op.execute(
            sa.text(
                f"""
                INSERT INTO user_merchant_aliases
                    (user_id, raw_name, normalized_name, merchant_id, category_id, source)
            SELECT DISTINCT ON (t.user_id, trim(t.merchant_name))
                    t.user_id,
                    trim(t.merchant_name),
                    {normalized_tx},
                    merchants.id,
                    t.category_id,
                    CASE WHEN t.receipt_upload_id IS NULL THEN 'manual' ELSE 'receipt' END
                FROM transactions t
                JOIN merchants ON merchants.normalized_name = {normalized_tx}
                WHERE t.merchant_name IS NOT NULL AND trim(t.merchant_name) <> ''
                ON CONFLICT (user_id, raw_name) DO NOTHING
                """,
            ),
        )
    else:
        op.execute(
            sa.text(
                f"""
                INSERT OR IGNORE INTO user_merchant_aliases
                    (user_id, raw_name, normalized_name, merchant_id, category_id, source)
                SELECT
                    t.user_id,
                    trim(t.merchant_name),
                    {normalized_tx},
                    merchants.id,
                    t.category_id,
                    CASE WHEN t.receipt_upload_id IS NULL THEN 'manual' ELSE 'receipt' END
                FROM transactions t
                JOIN merchants ON merchants.normalized_name = {normalized_tx}
                WHERE t.merchant_name IS NOT NULL AND trim(t.merchant_name) <> ''
                """,
            ),
        )


def downgrade() -> None:
    op.drop_index("ix_transactions_user_merchant", table_name="transactions")
    op.drop_index("ix_transactions_user_category_date", table_name="transactions")
    op.drop_index("ix_transactions_user_date", table_name="transactions")
    op.drop_index("ix_transactions_merchant_id", table_name="transactions")
    op.drop_constraint("fk_transactions_merchant_id_merchants", "transactions", type_="foreignkey")
    op.drop_column("transactions", "updated_at")
    op.drop_column("transactions", "source")
    op.drop_column("transactions", "raw_merchant_name")
    op.drop_column("transactions", "merchant_id")

    op.drop_index("ix_user_merchant_aliases_category_id", table_name="user_merchant_aliases")
    op.drop_index("ix_user_merchant_aliases_merchant_id", table_name="user_merchant_aliases")
    op.drop_index("ix_user_merchant_aliases_normalized_name", table_name="user_merchant_aliases")
    op.drop_index("ix_user_merchant_aliases_raw_name", table_name="user_merchant_aliases")
    op.drop_index("ix_user_merchant_aliases_user_id", table_name="user_merchant_aliases")
    op.drop_table("user_merchant_aliases")

    op.drop_index("ix_merchants_normalized_name", table_name="merchants")
    op.drop_table("merchants")
