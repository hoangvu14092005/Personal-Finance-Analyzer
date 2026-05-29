"""Account lifecycle APIs."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import User
from app.schemas.account import AccountDeleteRequest, AccountDeleteResponse
from app.services.audit import record_audit_event

router = APIRouter(prefix="/account", tags=["account"])

DELETE_GRACE_PERIOD_DAYS = 14


def _require_user(current_user: User) -> User:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return current_user


def _delete_response(user: User, *, message: str) -> AccountDeleteResponse:
    status_value = "pending" if user.account_deletion_requested_at is not None else "cancelled"
    return AccountDeleteResponse(
        status=status_value,
        requested_at=user.account_deletion_requested_at,
        scheduled_at=user.account_deletion_scheduled_at,
        cancelled_at=user.account_deletion_cancelled_at,
        message=message,
    )


@router.post("/delete-request", response_model=AccountDeleteResponse)
def request_account_deletion(
    payload: AccountDeleteRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AccountDeleteResponse:
    user = _require_user(current_user)
    now = datetime.now(tz=UTC)
    if user.account_deletion_requested_at is None:
        user.account_deletion_requested_at = now
        user.account_deletion_scheduled_at = now + timedelta(days=DELETE_GRACE_PERIOD_DAYS)
    user.account_deletion_cancelled_at = None
    if user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    record_audit_event(
        session,
        user_id=user.id,
        event="account.delete_requested",
        target_type="account",
        target_id=user.id,
        metadata={"reason_provided": bool(payload.reason)},
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    return _delete_response(
        user,
        message="Account deletion requested. Data removal is pending the grace period.",
    )


@router.post("/delete-request/cancel", response_model=AccountDeleteResponse)
def cancel_account_deletion(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AccountDeleteResponse:
    user = _require_user(current_user)
    user.account_deletion_requested_at = None
    user.account_deletion_scheduled_at = None
    user.account_deletion_cancelled_at = datetime.now(tz=UTC)
    if user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    record_audit_event(
        session,
        user_id=user.id,
        event="account.delete_cancelled",
        target_type="account",
        target_id=user.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return _delete_response(user, message="Account deletion request cancelled.")


__all__ = ["router"]
