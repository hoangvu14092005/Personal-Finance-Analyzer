from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from jwt import InvalidTokenError
from sqlmodel import Session

from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import verify_access_token
from app.models.entities import User


def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
) -> User:
    settings = get_settings()
    session_token = request.cookies.get(settings.session_cookie_name)
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = verify_access_token(session_token)
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        ) from None

    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
