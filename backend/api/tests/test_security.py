from __future__ import annotations

from app.core.security import (
    clear_auth_cookie,
    create_access_token,
    set_auth_cookie,
    verify_access_token,
)
from fastapi import Response


def test_create_and_verify_access_token_roundtrip() -> None:
    token = create_access_token(user_id=123, email="demo@example.com")

    payload = verify_access_token(token)

    assert payload["sub"] == "123"
    assert payload["email"] == "demo@example.com"
    assert payload["type"] == "access"


def test_set_auth_cookie_writes_session_cookie() -> None:
    response = Response()

    set_auth_cookie(response, "jwt-token")

    raw_headers = dict(response.headers)
    assert "set-cookie" in raw_headers
    assert "pfa_session=jwt-token" in raw_headers["set-cookie"]


def test_clear_auth_cookie_expires_cookie() -> None:
    response = Response()

    clear_auth_cookie(response)

    raw_headers = dict(response.headers)
    assert "set-cookie" in raw_headers
    assert "pfa_session=" in raw_headers["set-cookie"]
