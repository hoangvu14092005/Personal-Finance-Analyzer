"""Current user profile APIs."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import User
from app.schemas.users import UserProfileResponse, UserProfileUpdate
from app.services.settings import get_or_create_user_settings

router = APIRouter(prefix="/users", tags=["users"])


def _to_profile_response(user: User) -> UserProfileResponse:
    if user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        currency=user.currency,
        timezone=user.timezone,
        locale=user.locale,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.get("/me", response_model=UserProfileResponse)
def get_current_profile(current_user: User = Depends(get_current_user)) -> UserProfileResponse:
    return _to_profile_response(current_user)


@router.patch("/me", response_model=UserProfileResponse)
def update_current_profile(
    payload: UserProfileUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    update_data = payload.model_dump(exclude_unset=True)
    if "full_name" in update_data:
        current_user.full_name = payload.full_name
    if payload.currency is not None:
        current_user.currency = payload.currency.strip().upper()
    if payload.timezone is not None:
        current_user.timezone = payload.timezone.strip()
    if payload.locale is not None:
        current_user.locale = payload.locale.strip()

    settings = get_or_create_user_settings(session, current_user)
    settings.updated_at = datetime.now(tz=UTC)
    if payload.currency is not None:
        settings.default_currency = current_user.currency
    if payload.timezone is not None:
        settings.timezone = current_user.timezone
    if payload.locale is not None:
        settings.locale = current_user.locale
        settings.number_format_locale = current_user.locale

    session.add(current_user)
    session.add(settings)
    session.commit()
    session.refresh(current_user)
    return _to_profile_response(current_user)


@router.post("/me/avatar", status_code=status.HTTP_409_CONFLICT)
async def upload_current_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> None:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    await file.close()
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Avatar upload requires profile media storage and is not enabled yet",
    )


@router.delete("/me/avatar", status_code=status.HTTP_409_CONFLICT)
def delete_current_user_avatar(current_user: User = Depends(get_current_user)) -> None:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Avatar storage is not enabled yet",
    )


__all__ = ["router"]
