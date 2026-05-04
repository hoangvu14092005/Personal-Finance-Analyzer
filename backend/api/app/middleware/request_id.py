"""Request ID middleware: tạo unique ID cho mỗi request để tracing.

Flow:
1. Check header "X-Request-ID" từ client (hoặc generate UUID4)
2. Set vào ContextVar để accessible trong toàn bộ request lifecycle
3. Log request start/end với duration
4. Add "X-Request-ID" vào response header

Purpose: Tracing requests qua logs, debugging distributed systems.
"""
from __future__ import annotations

import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import get_settings
from app.core.logging import get_logger
from app.middleware.request_context import set_request_id

logger = get_logger("api.request")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware tạo unique request ID và log request lifecycle.
    
    Logs:
        request.start: method, path, request_id
        request.end: method, path, status, duration_ms, request_id
    """
    
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.settings = get_settings()

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Generate hoặc reuse request_id từ client
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
