"""Category suggestion baseline (Phase 3.3 baseline).

Strategy MVP:
1. Tra `UserMerchantMapping` cua user theo `normalized_merchant_name`.
2. Neu chua co mapping, tra `None` de caller fallback `Uncategorized`.

Khi user xac nhan transaction voi merchant + category cu the, caller co the
goi `remember_user_merchant_category` de luu mapping cho lan suy luan sau.
"""
from __future__ import annotations

from pfa_shared.utils import normalize_whitespace
from sqlmodel import Session, select

from app.models.entities import UserMerchantMapping


def normalize_merchant_name(value: str) -> str:
    """Chuan hoa ten merchant de tra cuu mapping deterministic."""
    return normalize_whitespace(value).casefold()


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
    normalized = normalize_merchant_name(merchant_name)
    existing = session.exec(
        select(UserMerchantMapping).where(
            UserMerchantMapping.user_id == user_id,
            UserMerchantMapping.normalized_merchant_name == normalized,
        ),
    ).first()

    if existing is None:
        mapping = UserMerchantMapping(
            user_id=user_id,
            raw_merchant_name=merchant_name,
            normalized_merchant_name=normalized,
            category_id=category_id,
        )
        session.add(mapping)
        session.commit()
        session.refresh(mapping)
        return mapping

    existing.category_id = category_id
    existing.raw_merchant_name = merchant_name
    session.add(existing)
    session.commit()
    session.refresh(existing)
    return existing
