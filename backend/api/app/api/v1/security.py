"""Security session APIs.

MVP note: auth currently uses a stateless HttpOnly JWT cookie, so there is no
server-side session table yet. These endpoints expose the current session shape
needed by Settings UI and clear the auth cookie for revoke actions.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import clear_auth_cookie
from app.dependencies.auth import get_current_user
from app.models.entities import User
from app.schemas.security import (
    LoginHistoryItemResponse,
    LoginHistoryResponse,
    SecuritySessionListResponse,
    SecuritySessionResponse,
)
from app.services.audit import list_audit_events, record_audit_event

router = APIRouter(prefix="/security", tags=["security"])


def _current_session(user: User) -> SecuritySessionResponse:
    if user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return SecuritySessionResponse(
        id="current",
        user_id=user.id,
        email=user.email,
        is_current=True,
        created_at=user.created_at,
    )


@router.get("/sessions", response_model=SecuritySessionListResponse)
def list_security_sessions(
    current_user: User = Depends(get_current_user),
) -> SecuritySessionListResponse:
    return SecuritySessionListResponse(items=[_current_session(current_user)])


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_security_session(
    session_id: str,
    response: Response,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    current = _current_session(current_user)
    if session_id != "current":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    record_audit_event(
        session,
        user_id=current.user_id,
        event="security.session_revoked",
        target_type="session",
        target_id=session_id,
        commit=True,
    )
    clear_auth_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_security_sessions(
    response: Response,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    current = _current_session(current_user)
    record_audit_event(
        session,
        user_id=current.user_id,
        event="security.sessions_revoked",
        target_type="session",
        target_id="all",
        commit=True,
    )
    clear_auth_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/login-history", response_model=LoginHistoryResponse)
def list_login_history(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> LoginHistoryResponse:
    current = _current_session(current_user)
    events = [
        event
        for event in list_audit_events(session, user_id=current.user_id, limit=100)
        if event.event in {"auth.login", "auth.register"}
    ]
    return LoginHistoryResponse(
        items=[
            LoginHistoryItemResponse(
                id=str(event.id),
                occurred_at=event.created_at,
                event=event.event,
            )
            for event in events[:20]
        ],
    )


__all__ = ["router"]
