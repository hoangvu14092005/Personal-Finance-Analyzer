"""Settings APIs for account/app preferences."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import User, UserSettings
from app.schemas.settings import (
    AISettingsResponse,
    AISettingsUpdate,
    FinanceSettingsResponse,
    FinanceSettingsUpdate,
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    PrivacySettingsResponse,
    PrivacySettingsUpdate,
)
from app.services.audit import record_audit_event
from app.services.settings import (
    get_or_create_user_settings,
    update_ai_settings,
    update_finance_settings,
    update_notification_settings,
    update_privacy_settings,
)

router = APIRouter(prefix="/settings", tags=["settings"])


def _record_settings_update(
    session: Session,
    user: User,
    *,
    event: str,
    fields: list[str],
) -> None:
    if user.id is None:
        return
    record_audit_event(
        session,
        user_id=user.id,
        event=event,
        target_type="settings",
        target_id=user.id,
        metadata={"fields": ",".join(sorted(fields))},
        commit=True,
    )


def _finance_response(settings: UserSettings) -> FinanceSettingsResponse:
    return FinanceSettingsResponse(
        default_currency=settings.default_currency,
        timezone=settings.timezone,
        locale=settings.locale,
        default_analytics_range=settings.default_analytics_range,  # type: ignore[arg-type]
        budget_month_start_day=settings.budget_month_start_day,
        number_format_locale=settings.number_format_locale,
        show_decimals=settings.show_decimals,
        updated_at=settings.updated_at,
    )


def _ai_response(settings: UserSettings) -> AISettingsResponse:
    return AISettingsResponse(
        allow_ai_data_processing=settings.allow_ai_data_processing,
        auto_generate_insights=settings.auto_generate_insights,
        assistant_use_history=settings.assistant_use_history,
        updated_at=settings.updated_at,
    )


def _privacy_response(settings: UserSettings) -> PrivacySettingsResponse:
    return PrivacySettingsResponse(
        receipt_file_retention_days=settings.receipt_file_retention_days,
        raw_prompt_retention_days=settings.raw_prompt_retention_days,
        updated_at=settings.updated_at,
    )


def _notification_response(settings: UserSettings) -> NotificationSettingsResponse:
    return NotificationSettingsResponse(
        email_notifications_enabled=settings.email_notifications_enabled,
        push_notifications_enabled=settings.push_notifications_enabled,
        budget_alerts_enabled=settings.budget_alerts_enabled,
        receipt_notifications_enabled=settings.receipt_notifications_enabled,
        insight_notifications_enabled=settings.insight_notifications_enabled,
        updated_at=settings.updated_at,
    )


@router.get("/finance", response_model=FinanceSettingsResponse)
def get_finance_settings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FinanceSettingsResponse:
    settings = get_or_create_user_settings(session, current_user)
    return _finance_response(settings)


@router.patch("/finance", response_model=FinanceSettingsResponse)
def patch_finance_settings(
    payload: FinanceSettingsUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FinanceSettingsResponse:
    settings = update_finance_settings(session, current_user, payload)
    _record_settings_update(
        session,
        current_user,
        event="settings.finance_updated",
        fields=list(payload.model_dump(exclude_unset=True).keys()),
    )
    return _finance_response(settings)


@router.get("/ai", response_model=AISettingsResponse)
def get_ai_settings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AISettingsResponse:
    settings = get_or_create_user_settings(session, current_user)
    return _ai_response(settings)


@router.patch("/ai", response_model=AISettingsResponse)
def patch_ai_settings(
    payload: AISettingsUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AISettingsResponse:
    settings = update_ai_settings(session, current_user, payload)
    _record_settings_update(
        session,
        current_user,
        event="settings.ai_updated",
        fields=list(payload.model_dump(exclude_unset=True).keys()),
    )
    return _ai_response(settings)


@router.get("/notifications", response_model=NotificationSettingsResponse)
def get_notification_settings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> NotificationSettingsResponse:
    settings = get_or_create_user_settings(session, current_user)
    return _notification_response(settings)


@router.patch("/notifications", response_model=NotificationSettingsResponse)
def patch_notification_settings(
    payload: NotificationSettingsUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> NotificationSettingsResponse:
    settings = update_notification_settings(session, current_user, payload)
    _record_settings_update(
        session,
        current_user,
        event="settings.notifications_updated",
        fields=list(payload.model_dump(exclude_unset=True).keys()),
    )
    return _notification_response(settings)


@router.get("/privacy", response_model=PrivacySettingsResponse)
def get_privacy_settings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PrivacySettingsResponse:
    settings = get_or_create_user_settings(session, current_user)
    return _privacy_response(settings)


@router.patch("/privacy", response_model=PrivacySettingsResponse)
def patch_privacy_settings(
    payload: PrivacySettingsUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PrivacySettingsResponse:
    settings = update_privacy_settings(session, current_user, payload)
    _record_settings_update(
        session,
        current_user,
        event="settings.privacy_updated",
        fields=list(payload.model_dump(exclude_unset=True).keys()),
    )
    return _privacy_response(settings)


__all__ = ["router"]
