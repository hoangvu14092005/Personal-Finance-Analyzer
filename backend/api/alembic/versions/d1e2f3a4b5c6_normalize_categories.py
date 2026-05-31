"""normalize categories — add "Thực phẩm & siêu thị", merge English duplicates

Chuẩn hóa hệ danh mục về tiếng Việt thống nhất (15 nhóm):
1. Thêm category hệ thống "Thực phẩm & siêu thị" (nếu chưa có).
2. Gộp các category tiếng Anh cũ (Food, Transport, Shopping, Bills, Health,
   Education, Entertainment, Other) + "Hóa đơn" (trùng "Hóa đơn & tiện ích")
   về category tiếng Việt tương ứng: repoint mọi FK rồi xóa category cũ.
3. Xử lý xung đột UNIQUE budgets (user_id, category_id, period_month):
   nếu target đã có budget cùng kỳ → xóa budget nguồn thay vì repoint.

Idempotent + an toàn: chỉ thao tác khi category nguồn/đích tồn tại. Trên môi
trường không có category tiếng Anh, migration là no-op.

Revision ID: d1e2f3a4b5c6
Revises: c8d9e0f1a2b3
Create Date: 2026-05-31 19:30:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d1e2f3a4b5c6"
down_revision = "c8d9e0f1a2b3"
branch_labels = None
depends_on = None

NEW_CATEGORY = ("Thực phẩm & siêu thị", "#22c55e")

# (source_name_cũ -> target_name_việt)
MERGE_MAP: list[tuple[str, str]] = [
    ("Food", "Ăn uống"),
    ("Transport", "Di chuyển"),
    ("Shopping", "Mua sắm"),
    ("Bills", "Hóa đơn & tiện ích"),
    ("Health", "Sức khỏe & y tế"),
    ("Education", "Giáo dục"),
    ("Entertainment", "Giải trí"),
    ("Other", "Khác"),
    ("Hóa đơn", "Hóa đơn & tiện ích"),
]

# Các bảng có cột category_id trỏ tới categories.id (ngoài budgets xử lý riêng).
# user_merchant_mappings: UNIQUE trên (user_id, normalized name) → đổi category_id an toàn.
SIMPLE_FK_TABLES = [
    "transactions",
    "receipt_line_items",
    "user_merchant_aliases",
    "user_merchant_mappings",
]


def _system_category_id(bind: sa.engine.Connection, name: str) -> int | None:
    row = bind.execute(
        sa.text(
            "SELECT id FROM categories "
            "WHERE name = :name AND is_system = true AND user_id IS NULL "
            "ORDER BY id LIMIT 1",
        ),
        {"name": name},
    ).first()
    return int(row[0]) if row else None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Thêm category mới (idempotent).
    if _system_category_id(bind, NEW_CATEGORY[0]) is None:
        bind.execute(
            sa.text(
                "INSERT INTO categories (user_id, name, color, is_system) "
                "VALUES (NULL, :name, :color, true)",
            ),
            {"name": NEW_CATEGORY[0], "color": NEW_CATEGORY[1]},
        )

    # 2. Gộp tiếng Anh -> tiếng Việt.
    for source_name, target_name in MERGE_MAP:
        source_id = _system_category_id(bind, source_name)
        target_id = _system_category_id(bind, target_name)
        if source_id is None or target_id is None or source_id == target_id:
            continue

        # 2a. Repoint các bảng FK đơn giản.
        for table in SIMPLE_FK_TABLES:
            bind.execute(
                sa.text(
                    f"UPDATE {table} SET category_id = :target "  # noqa: S608 - tên bảng từ hằng số nội bộ
                    "WHERE category_id = :source",
                ),
                {"target": target_id, "source": source_id},
            )

        # 2b. Budgets: xử lý xung đột UNIQUE (user_id, category_id, period_month).
        # Xóa budget nguồn nào mà target đã có cùng (user, kỳ); còn lại repoint.
        bind.execute(
            sa.text(
                "DELETE FROM budgets b_src "
                "WHERE b_src.category_id = :source "
                "AND EXISTS ("
                "  SELECT 1 FROM budgets b_tgt "
                "  WHERE b_tgt.category_id = :target "
                "  AND b_tgt.user_id = b_src.user_id "
                "  AND b_tgt.period_month = b_src.period_month"
                ")",
            ),
            {"source": source_id, "target": target_id},
        )
        bind.execute(
            sa.text("UPDATE budgets SET category_id = :target WHERE category_id = :source"),
            {"target": target_id, "source": source_id},
        )

        # 2c. Xóa category tiếng Anh cũ.
        bind.execute(
            sa.text("DELETE FROM categories WHERE id = :source"),
            {"source": source_id},
        )


def downgrade() -> None:
    # Gộp là thao tác phá hủy (không lưu category_id gốc của từng row), nên
    # downgrade chỉ xóa category mới thêm. KHÔNG khôi phục category tiếng Anh.
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM categories "
            "WHERE name = :name AND is_system = true AND user_id IS NULL",
        ),
        {"name": NEW_CATEGORY[0]},
    )
