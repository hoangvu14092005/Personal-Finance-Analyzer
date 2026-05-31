"""seed system categories

User mới đăng ký trước đây có 0 category, và không migration nào seed bộ category
hệ thống → LLM/phân loại không có "đích" để map vào. Migration này seed 14 nhóm
category hệ thống dùng chung (`is_system=True`, `user_id=NULL`).

Idempotent: chỉ insert category chưa tồn tại (theo name + is_system + user_id NULL).

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-05-31 09:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c8d9e0f1a2b3"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None

# (name, color) — màu cho UI. Thứ tự = thứ tự hiển thị mặc định.
SYSTEM_CATEGORIES: list[tuple[str, str]] = [
    ("Ăn uống", "#f59e0b"),
    ("Cà phê & đồ uống", "#d97706"),
    ("Thực phẩm & siêu thị", "#22c55e"),
    ("Di chuyển", "#10b981"),
    ("Mua sắm", "#3b82f6"),
    ("Hóa đơn & tiện ích", "#ef4444"),
    ("Giải trí", "#8b5cf6"),
    ("Sức khỏe & y tế", "#ec4899"),
    ("Giáo dục", "#0ea5e9"),
    ("Nhà ở", "#6366f1"),
    ("Du lịch", "#14b8a6"),
    ("Làm đẹp & chăm sóc cá nhân", "#f472b6"),
    ("Quà tặng & quyên góp", "#a855f7"),
    ("Chuyển khoản & rút tiền", "#64748b"),
    ("Khác", "#a3a3a3"),
]


def upgrade() -> None:
    bind = op.get_bind()
    categories = sa.table(
        "categories",
        sa.column("user_id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("color", sa.String),
        sa.column("is_system", sa.Boolean),
    )
    for name, color in SYSTEM_CATEGORIES:
        exists = bind.execute(
            sa.text(
                "SELECT 1 FROM categories "
                "WHERE name = :name AND is_system = true AND user_id IS NULL "
                "LIMIT 1",
            ),
            {"name": name},
        ).first()
        if exists is None:
            bind.execute(
                categories.insert().values(
                    user_id=None,
                    name=name,
                    color=color,
                    is_system=True,
                ),
            )


def downgrade() -> None:
    bind = op.get_bind()
    names = [name for name, _ in SYSTEM_CATEGORIES]
    bind.execute(
        sa.text(
            "DELETE FROM categories "
            "WHERE is_system = true AND user_id IS NULL AND name = ANY(:names)",
        ),
        {"names": names},
    )
