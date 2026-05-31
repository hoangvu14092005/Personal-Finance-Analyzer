"""Category suggestion (G1 — LLM classification).

Thứ tự suy luận category cho 1 merchant:
1. `UserMerchantAlias` (đã học từ lần trước, gồm cả kết quả LLM đã cache).
2. `UserMerchantMapping` (legacy mapping, tương thích ngược).
3. LLM phân loại — CHỈ khi user bật `allow_ai_data_processing`. Kết quả được
   cache lại thành alias `source="llm"` để lần sau không phải gọi LLM nữa.
4. None → caller fallback "Chưa phân loại".

Khi user xác nhận transaction với merchant + category cụ thể, caller gọi
`remember_user_merchant_category` để lưu mapping (source="manual").
"""
from __future__ import annotations

from sqlmodel import Session, col, or_, select

from app.models.entities import Category, UserMerchantMapping, UserSettings
from app.services.category_classifier import classify_merchant_category
from app.services.merchants import (
    get_or_create_user_merchant_alias,
    mirror_legacy_user_merchant_mapping,
    normalize_merchant_name,
    suggest_category_for_user_merchant_alias,
)


def _user_allows_ai(session: Session, user_id: int) -> bool:
    """Đọc cờ allow_ai_data_processing. Mặc định True nếu chưa có settings row."""
    settings = session.exec(
        select(UserSettings).where(UserSettings.user_id == user_id),
    ).first()
    if settings is None:
        return True
    return settings.allow_ai_data_processing


def _list_user_categories(session: Session, user_id: int) -> list[tuple[int, str]]:
    """Danh sách (id, name) category khả dụng cho user: system + của chính user."""
    rows = session.exec(
        select(Category)
        .where(
            or_(
                col(Category.is_system).is_(True),
                Category.user_id == user_id,
            ),
        )
        .order_by(col(Category.is_system).desc(), col(Category.name).asc()),
    ).all()
    return [(c.id, c.name) for c in rows if c.id is not None]


def suggest_category_for_merchant(
    session: Session,
    user_id: int,
    merchant_name: str | None,
) -> int | None:
    """Trả category_id gợi ý cho merchant theo thứ tự alias → mapping → LLM."""
    if not merchant_name:
        return None

    normalized = normalize_merchant_name(merchant_name)
    if not normalized:
        return None

    # 1. Alias đã học (gồm cả kết quả LLM đã cache).
    alias_category_id = suggest_category_for_user_merchant_alias(
        session,
        user_id=user_id,
        merchant_name=merchant_name,
    )
    if alias_category_id is not None:
        return alias_category_id

    # 2. Legacy mapping.
    mapping = session.exec(
        select(UserMerchantMapping).where(
            UserMerchantMapping.user_id == user_id,
            UserMerchantMapping.normalized_merchant_name == normalized,
        ),
    ).first()
    if mapping is not None and mapping.category_id is not None:
        return mapping.category_id

    # 3. LLM phân loại (chỉ khi user cho phép xử lý dữ liệu bằng AI).
    if not _user_allows_ai(session, user_id):
        return None

    categories = _list_user_categories(session, user_id)
    if not categories:
        return None

    category_id = classify_merchant_category(merchant_name, categories)
    if category_id is None:
        return None

    # Cache kết quả LLM thành alias để lần sau không gọi lại.
    get_or_create_user_merchant_alias(
        session,
        user_id=user_id,
        raw_name=merchant_name,
        category_id=category_id,
        source="llm",
        confidence=None,
    )
    session.commit()
    return category_id


def remember_user_merchant_category(
    session: Session,
    user_id: int,
    merchant_name: str,
    category_id: int,
) -> UserMerchantMapping:
    """Lưu hoặc cập nhật mapping merchant -> category cho user (source=manual)."""
    get_or_create_user_merchant_alias(
        session,
        user_id=user_id,
        raw_name=merchant_name,
        category_id=category_id,
        source="manual",
        confidence=1.0,
    )
    existing = mirror_legacy_user_merchant_mapping(
        session,
        user_id=user_id,
        merchant_name=merchant_name,
        category_id=category_id,
    )
    session.commit()
    session.refresh(existing)
    return existing
