"""Category suggestion baseline (Phase 3.3 baseline).

Strategy MVP:
1. Tra `UserMerchantMapping` cua user theo `normalized_merchant_name`.
2. Neu chua co mapping, tra `None` de caller fallback `Uncategorized`.

Khi user xac nhan transaction voi merchant + category cu the, caller co the
goi `remember_user_merchant_category` de luu mapping cho lan suy luan sau.
"""
from __future__ import annotations

from sqlmodel import Session, select

from app.models.entities import UserMerchantMapping
from app.services.merchants import (
    get_or_create_user_merchant_alias,
    mirror_legacy_user_merchant_mapping,
    normalize_merchant_name,
    suggest_category_for_user_merchant_alias,
)


def suggest_category_for_merchant(
    session: Session,
    user_id: int,
    merchant_name: str | None,
) -> int | None:
    """Tra category_id goi y dua tren mapping da hoc cua user."""
    if not merchant_name:
        return None

    normalized = normalize_merchant_name(merchant_name)
    if not normalized:
        return None

    alias_category_id = suggest_category_for_user_merchant_alias(
        session,
        user_id=user_id,
        merchant_name=merchant_name,
    )
    if alias_category_id is not None:
        return alias_category_id

    mapping = session.exec(
        select(UserMerchantMapping).where(
            UserMerchantMapping.user_id == user_id,
            UserMerchantMapping.normalized_merchant_name == normalized,
        ),
    ).first()

    if mapping is None or mapping.category_id is None:
        return None

    return mapping.category_id


def remember_user_merchant_category(
    session: Session,
    user_id: int,
    merchant_name: str,
    category_id: int,
) -> UserMerchantMapping:
    """Luu hoac cap nhat mapping merchant -> category cho user."""
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
