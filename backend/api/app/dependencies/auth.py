"""FastAPI dependency: extract authenticated user từ JWT cookie.

Flow:
1. Extract token từ cookie "pfa_session"
2. Verify JWT signature và expiration
3. Query user từ DB
4. Return User object

Raises HTTPException 401 nếu: token missing, invalid, expired, hoặc user not found.
"""
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
    """Extract authenticated user từ JWT cookie.
    
    Usage:
        @router.get("/api/v1/auth/me")
        def get_me(user: User = Depends(get_current_user)):
            return UserResponse.from_orm(user)
    
    Raises:
        HTTPException 401: Not authenticated, invalid session, hoặc user not found
    """
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
