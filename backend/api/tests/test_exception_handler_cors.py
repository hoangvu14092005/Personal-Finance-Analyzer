"""Bug 3 — `global_exception_handler` chỉ reflect Origin trong whitelist.

Gọi handler trực tiếp (không cần route lỗi) để kiểm tra header CORS trên 500.
"""
from __future__ import annotations

import asyncio
import json

from app.main import global_exception_handler, settings
from starlette.requests import Request


def _request_with_origin(origin: str | None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if origin is not None:
        headers.append((b"origin", origin.encode()))
    scope = {"type": "http", "method": "GET", "path": "/", "headers": headers}
    return Request(scope)


def _invoke(origin: str | None):
    request = _request_with_origin(origin)
    return asyncio.run(global_exception_handler(request, RuntimeError("boom")))


def test_whitelisted_origin_is_reflected() -> None:
    origin = settings.parsed_cors_origins[0]
    response = _invoke(origin)
    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
    assert json.loads(response.body) == {"detail": "Internal server error"}


def test_non_whitelisted_origin_is_not_reflected() -> None:
    response = _invoke("https://evil.example")
    assert response.status_code == 500
    assert "access-control-allow-origin" not in response.headers
    assert "access-control-allow-credentials" not in response.headers
    assert json.loads(response.body) == {"detail": "Internal server error"}


def test_missing_origin_has_no_cors_headers() -> None:
    response = _invoke(None)
    assert response.status_code == 500
    assert "access-control-allow-origin" not in response.headers
    assert json.loads(response.body) == {"detail": "Internal server error"}
