"""Bug 4 — `get_current_user` kiểm tra token type / is_active / deletion-pending.

Gọi dependency trực tiếp với Request dựng tay (mang cookie JWT) + db_session.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from app.core.config import get_settings
from app.core.security import ALGORITHM, create_access_token
from app.dependencies.auth import (
    get_current_user,
    get_current_user_allow_deletion_pending,
)
from app.models.entities import User
from fastapi import HTTPException
from sqlalchemy.engine import Engine
from sqlmodel import Session
from starlette.requests import Request


def _seed_user(
    engine: Engine,
    *,
    is_active: bool = True,
    deletion_requested: bool = False,
) -> User:
    with Session(engine) as session:
        user = User(
            email="state@example.com",
            password_hash="hashed",
            is_active=is_active,
            account_deletion_requested_at=(
                datetime.now(tz=UTC) if deletion_requested else None
            ),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    if user.id is None:
        raise AssertionError("seeded user must have id")
    return user


def _request_with_token(token: str) -> Request:
    cookie_name = get_settings().session_cookie_name
    headers = [(b"cookie", f"{cookie_name}={token}".encode())]
    scope = {"type": "http", "method": "GET", "path": "/", "headers": headers}
    return Request(scope)


def _non_access_token(user_id: int) -> str:
    settings = get_settings()
    now = datetime.now(tz=UTC)
    payload = {
        "sub": str(user_id),
        "email": "state@example.com",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=30)).timestamp()),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


# --- Bug condition C(X): phải bị từ chối 401 ---

def test_inactive_user_rejected(engine: Engine, db_session: Session) -> None:
    user = _seed_user(engine, is_active=False)
    token = create_access_token(user_id=user.id or 0, email=user.email)
    with pytest.raises(HTTPException) as exc:
        get_current_user(_request_with_token(token), db_session)
    assert exc.value.status_code == 401


def test_non_access_token_rejected(engine: Engine, db_session: Session) -> None:
    user = _seed_user(engine)
    token = _non_access_token(user.id or 0)
    with pytest.raises(HTTPException) as exc:
        get_current_user(_request_with_token(token), db_session)
    assert exc.value.status_code == 401


def test_deletion_pending_user_rejected(engine: Engine, db_session: Session) -> None:
    user = _seed_user(engine, deletion_requested=True)
    token = create_access_token(user_id=user.id or 0, email=user.email)
    with pytest.raises(HTTPException) as exc:
        get_current_user(_request_with_token(token), db_session)
    assert exc.value.status_code == 401


# --- Preservation ¬C(X): vẫn trả User / vẫn 401 cho lỗi token cũ ---

def test_valid_active_user_returns_user(engine: Engine, db_session: Session) -> None:
    user = _seed_user(engine)
    token = create_access_token(user_id=user.id or 0, email=user.email)
    result = get_current_user(_request_with_token(token), db_session)
    assert result.id == user.id


def test_missing_cookie_rejected(db_session: Session) -> None:
    scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
    with pytest.raises(HTTPException) as exc:
        get_current_user(Request(scope), db_session)
    assert exc.value.status_code == 401


def test_invalid_token_rejected(db_session: Session) -> None:
    with pytest.raises(HTTPException) as exc:
        get_current_user(_request_with_token("not-a-valid-jwt"), db_session)
    assert exc.value.status_code == 401


# --- Exception policy: cancel endpoint dependency cho phép deletion-pending ---

def test_allow_deletion_pending_returns_user(engine: Engine, db_session: Session) -> None:
    user = _seed_user(engine, deletion_requested=True)
    token = create_access_token(user_id=user.id or 0, email=user.email)
    result = get_current_user_allow_deletion_pending(_request_with_token(token), db_session)
    assert result.id == user.id


def test_allow_deletion_pending_still_checks_inactive(
    engine: Engine, db_session: Session,
) -> None:
    user = _seed_user(engine, is_active=False, deletion_requested=True)
    token = create_access_token(user_id=user.id or 0, email=user.email)
    with pytest.raises(HTTPException) as exc:
        get_current_user_allow_deletion_pending(_request_with_token(token), db_session)
    assert exc.value.status_code == 401
