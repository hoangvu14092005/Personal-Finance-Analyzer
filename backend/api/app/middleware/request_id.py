from __future__ import annotations

import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import get_settings
from app.core.logging import get_logger
from app.middleware.request_context import set_request_id

logger = get_logger("api.request")


class RequestIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = request.headers.get(self.settings.request_id_header) or str(uuid4())
        set_request_id(request_id)

        start = time.perf_counter()
        logger.info(
            "request.start method=%s path=%s request_id=%s",
            request.method,
            request.url.path,
            request_id,
        )

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers[self.settings.request_id_header] = request_id
        logger.info(
            "request.end method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        return response
