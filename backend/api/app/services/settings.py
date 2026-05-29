"""Settings service layer."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session, select

from app.models.entities import User, UserSettings
from app.schemas.settings import (
    AISettingsUpdate,
    FinanceSettingsUpdate,
    NotificationSettingsUpdate,
    PrivacySettingsUpdate,
)


def get_or_create_user_settings(
    session: Session,
    user: User,
) -> UserSettings:
    """Return settings row, creating one from `users` profile defaults if missing."""
    if user.id is None:
        raise ValueError("User id missing")

    settings = session.exec(
        select(UserSettings).where(UserSettings.user_id == user.id),
    ).first()
    if settings is not None:
        return settings

    settings = UserSettings(
        user_id=user.id,
        default_currency=user.currency,
        timezone=user.timezone,
        locale=user.locale,
        number_format_locale=user.locale,
    )
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


def _apply_updates(target: UserSettings, updates: dict[str, Any]) -> None:
    for field, value in updates.items():
        if value is not None:
            setattr(target, field, value)
    target.updated_at = datetime.now(tz=UTC)


def update_finance_settings(
    session: Session,
    user: User,
    payload: FinanceSettingsUpdate,
) -> UserSettings:
    settings = get_or_create_user_settings(session, user)
    update_data = payload.model_dump(exclude_unset=True)
    _apply_updates(settings, update_data)

    # Keep legacy profile fields in sync while the rest of the app still reads User.
    if payload.default_currency is not None:
        user.currency = payload.default_currency
    if payload.timezone is not None:
        user.timezone = payload.timezone
    if payload.locale is not None:
        user.locale = payload.locale

    session.add(settings)
    session.add(user)
    session.commit()
    session.refresh(settings)
    return settings


def update_ai_settings(
    session: Session,
    user: User,
    payload: AISettingsUpdate,
) -> UserSettings:
    settings = get_or_create_user_settings(session, user)
    _apply_updates(settings, payload.model_dump(exclude_unset=True))
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


def update_privacy_settings(
    session: Session,
    user: User,
    payload: PrivacySettingsUpdate,
) -> UserSettings:
    settings = get_or_create_user_settings(session, user)
    _apply_updates(settings, payload.model_dump(exclude_unset=True))
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


def update_notification_settings(
    session: Session,
    user: User,
    payload: NotificationSettingsUpdate,
) -> UserSettings:
    settings = get_or_create_user_settings(session, user)
    _apply_updates(settings, payload.model_dump(exclude_unset=True))
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


__all__ = [
    "get_or_create_user_settings",
    "update_ai_settings",
    "update_finance_settings",
    "update_notification_settings",
    "update_privacy_settings",
]
