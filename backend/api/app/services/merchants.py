from __future__ import annotations

from datetime import UTC, datetime

from pfa_shared.utils import normalize_whitespace
from sqlmodel import Session, col, select

from app.models.entities import Merchant, UserMerchantAlias, UserMerchantMapping
from app.schemas.merchants import MerchantSearchItemResponse


def normalize_merchant_name(value: str) -> str:
    """Normalize merchant text for deterministic lookup."""
    return normalize_whitespace(value).casefold()


def get_or_create_merchant(
    session: Session,
    raw_name: str,
    *,
    display_name: str | None = None,
) -> Merchant | None:
    """Return the global Merchant for a raw merchant name, creating it if needed."""
    normalized = normalize_merchant_name(raw_name)
    if not normalized:
        return None

    merchant = session.exec(
        select(Merchant).where(Merchant.normalized_name == normalized),
    ).first()
    if merchant is not None:
        return merchant

    merchant = Merchant(
        normalized_name=normalized,
        display_name=(display_name or normalize_whitespace(raw_name))[:255],
    )
    session.add(merchant)
    session.flush()
    session.refresh(merchant)
    return merchant


def get_or_create_user_merchant_alias(
    session: Session,
    *,
    user_id: int,
    raw_name: str,
    category_id: int | None = None,
    source: str = "manual",
    confidence: float | None = None,
) -> UserMerchantAlias | None:
    """Upsert user alias and linked global merchant.

    The transaction remains the financial source of truth; this alias is a
    learning/search helper for category suggestions and future merchant reports.
    """
    raw_clean = normalize_whitespace(raw_name)[:255]
    normalized = normalize_merchant_name(raw_clean)
    if not raw_clean or not normalized:
        return None

    merchant = get_or_create_merchant(session, raw_clean)
    if merchant is None or merchant.id is None:
        return None

    alias = session.exec(
        select(UserMerchantAlias).where(
            UserMerchantAlias.user_id == user_id,
            UserMerchantAlias.raw_name == raw_clean,
        ),
    ).first()
    now = datetime.now(tz=UTC)

    if alias is None:
        alias = UserMerchantAlias(
            user_id=user_id,
            raw_name=raw_clean,
            normalized_name=normalized,
            merchant_id=merchant.id,
            category_id=category_id,
            confidence=confidence,
            source=source,
            last_used_at=now,
        )
        session.add(alias)
        session.flush()
        session.refresh(alias)
        return alias

    alias.normalized_name = normalized
    alias.merchant_id = merchant.id
    if category_id is not None:
        alias.category_id = category_id
    if confidence is not None:
        alias.confidence = confidence
    alias.source = source
    alias.last_used_at = now
    session.add(alias)
    session.flush()
    session.refresh(alias)
    return alias


def suggest_category_for_user_merchant_alias(
    session: Session,
    *,
    user_id: int,
    merchant_name: str | None,
) -> int | None:
    """Suggest category from the new alias table."""
    if not merchant_name:
        return None

    normalized = normalize_merchant_name(merchant_name)
    if not normalized:
        return None

    alias = session.exec(
        select(UserMerchantAlias)
        .where(
            UserMerchantAlias.user_id == user_id,
            UserMerchantAlias.normalized_name == normalized,
        )
        .order_by(UserMerchantAlias.last_used_at.desc()),
    ).first()

    return alias.category_id if alias is not None else None


def mirror_legacy_user_merchant_mapping(
    session: Session,
    *,
    user_id: int,
    merchant_name: str,
    category_id: int,
) -> UserMerchantMapping:
    """Keep legacy mapping in sync while callers/tests still read it."""
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
        session.flush()
        session.refresh(mapping)
        return mapping

    existing.raw_merchant_name = merchant_name
    existing.category_id = category_id
    session.add(existing)
    session.flush()
    session.refresh(existing)
    return existing


def search_merchants_for_user(
    session: Session,
    *,
    user_id: int,
    query: str,
    limit: int = 10,
) -> list[MerchantSearchItemResponse]:
    """Search global merchants plus user-specific aliases.

    Alias matches are returned first because they carry user-specific category
    learning. Global merchant matches fill the remaining slots.
    """
    clean_query = normalize_whitespace(query)
    normalized_query = normalize_merchant_name(clean_query)
    if not normalized_query:
        return []

    like_pattern = f"%{normalized_query}%"
    alias_rows = session.exec(
        select(UserMerchantAlias)
        .where(UserMerchantAlias.user_id == user_id)
        .where(
            col(UserMerchantAlias.normalized_name).ilike(like_pattern)
            | col(UserMerchantAlias.raw_name).ilike(f"%{clean_query}%"),
        )
        .order_by(col(UserMerchantAlias.last_used_at).desc())
        .limit(limit),
    ).all()

    results: list[MerchantSearchItemResponse] = []
    seen_merchant_ids: set[int] = set()
    for alias in alias_rows:
        merchant = session.get(Merchant, alias.merchant_id)
        if merchant is None or merchant.id is None:
            continue
        seen_merchant_ids.add(merchant.id)
        results.append(
            MerchantSearchItemResponse(
                merchant_id=merchant.id,
                display_name=merchant.display_name,
                normalized_name=merchant.normalized_name,
                raw_name=alias.raw_name,
                category_id=alias.category_id,
                confidence=alias.confidence,
                source=alias.source,
                last_used_at=alias.last_used_at,
                match_type="alias",
            ),
        )

    remaining = max(0, limit - len(results))
    if remaining == 0:
        return results

    merchant_rows = session.exec(
        select(Merchant)
        .where(
            col(Merchant.normalized_name).ilike(like_pattern)
            | col(Merchant.display_name).ilike(f"%{clean_query}%"),
        )
        .order_by(col(Merchant.display_name).asc())
        .limit(limit),
    ).all()
    for merchant in merchant_rows:
        if merchant.id is None or merchant.id in seen_merchant_ids:
            continue
        results.append(
            MerchantSearchItemResponse(
                merchant_id=merchant.id,
                display_name=merchant.display_name,
                normalized_name=merchant.normalized_name,
                match_type="merchant",
            ),
        )
        if len(results) >= limit:
            break
    return results
