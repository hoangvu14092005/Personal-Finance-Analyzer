"""FastAPI dependency: extract authenticated user từ JWT cookie.

Flow:
1. Extract token từ cookie "pfa_session"
2. Verify JWT signature và expiration
3. Kiểm tra token type == "access"
4. Query user từ DB và kiểm tra trạng thái (is_active, deletion-pending)
5. Return User object

Raises HTTPException 401 nếu: token missing/invalid/expired/sai loại, user not
found, user inactive, hoặc (mặc định) tài khoản đang chờ xóa.

Hai dependency:
- `get_current_user`: dùng cho hầu hết endpoint protected. Chặn tài khoản đang
  chờ xóa (`account_deletion_requested_at IS NOT NULL`) bằng 401.
- `get_current_user_allow_deletion_pending`: dùng cho endpoint hủy yêu cầu xóa
  (và request xóa) để user trong grace period vẫn truy cập được — vẫn kiểm tra
  token type + is_active.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from jwt import InvalidTokenError
from sqlmodel import Session

from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import verify_access_token
from app.models.entities import User


def _authenticate(
    request: Request,
    session: Session,
    *,
    allow_deletion_pending: bool,
) -> User:
    """Logic xác thực chung cho cả hai dependency.

    Args:
        allow_deletion_pending: nếu True, KHÔNG chặn tài khoản đang chờ xóa
            (dùng cho endpoint hủy yêu cầu xóa). Token type + is_active vẫn
            luôn được kiểm tra.
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
        token_type = payload.get("type")
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        ) from None

    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
        )

    if not allow_deletion_pending and user.account_deletion_requested_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is pending deletion",
        )

    return user


def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
) -> User:
    """Extract authenticated user từ JWT cookie cho endpoint protected.

    Usage:
        @router.get("/api/v1/auth/me")
        def get_me(user: User = Depends(get_current_user)):
            return UserResponse.from_orm(user)

    Raises:
        HTTPException 401: not authenticated, invalid/expired session, sai loại
            token, user not found, user inactive, hoặc tài khoản đang chờ xóa.
    """
    return _authenticate(request, session, allow_deletion_pending=False)


def get_current_user_allow_deletion_pending(
    request: Request,
    session: Session = Depends(get_session),
) -> User:
    """Như `get_current_user` nhưng KHÔNG chặn tài khoản đang chờ xóa.

    Dùng cho các endpoint vòng đời tài khoản (hủy / yêu cầu xóa) để user trong
    grace period không bị kẹt. Vẫn kiểm tra token type và is_active.
    """
    return _authenticate(request, session, allow_deletion_pending=True)
