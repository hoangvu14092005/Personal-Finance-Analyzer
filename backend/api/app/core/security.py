"""JWT authentication và cookie management.

Security:
- JWT secret >= 32 chars trong production
- Cookies: httponly=True (XSS protection), secure=True (HTTPS only)
- Tokens expire sau 30 phút (default)
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import Response

from app.core.config import get_settings

ALGORITHM = "HS256"  # HMAC with SHA-256


def create_access_token(user_id: int, email: str) -> str:
    """Tạo JWT access token.
    
    Payload: {sub: user_id, email, iat, exp, type: "access"}
    Token không thể revoke (stateless) - phải đợi expire.
    """
    settings = get_settings()
    now = datetime.now(tz=UTC)
    expires_at = now + timedelta(minutes=settings.jwt_access_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def verify_access_token(token: str) -> dict[str, Any]:
    """Verify JWT token.
    
    Raises:
        jwt.ExpiredSignatureError: Token hết hạn
        jwt.InvalidTokenError: Token invalid
    """
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


def set_auth_cookie(response: Response, token: str) -> None:
    """Set auth cookie với httponly=True, secure (prod), samesite=lax."""
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,  # XSS protection
        secure=settings.session_cookie_secure,  # HTTPS only (prod)
        samesite=settings.session_cookie_samesite,  # CSRF protection
        max_age=settings.jwt_access_expire_minutes * 60,
        path="/",
        domain="localhost",  # Allow cookie to work across localhost and 127.0.0.1
    )


def clear_auth_cookie(response: Response) -> None:
    """Xóa auth cookie (logout). Token vẫn valid đến khi expire."""
    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        domain="localhost",
    )
