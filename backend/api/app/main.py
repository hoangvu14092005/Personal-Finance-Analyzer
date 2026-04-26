from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.categories import router as categories_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.receipts import router as receipts_router
from app.api.v1.transactions import router as transactions_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.middleware.request_id import RequestIdMiddleware
from app.services.ocr_queue import shutdown_ocr_broker, startup_ocr_broker

settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan: khởi động OCR broker khi app start, đóng khi shutdown.

    Khi Redis down, `startup_ocr_broker()` log warning và trả về False — app
    vẫn chạy được; `enqueue_ocr_job` sẽ fail-soft → endpoint upload rollback
    sang UPLOADED + error_code=queue_unavailable (xem `api/v1/receipts.py`).
    """
    await startup_ocr_broker()
    try:
        yield
    finally:
        await shutdown_ocr_broker()


app = FastAPI(
    title="Personal Finance Analyzer API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS cho phép frontend từ domain khác gọi API.
# allow_origins: danh sách domain được phép gọi.
# allow_methods: chấp nhận tất cả HTTP methods (GET, POST, PUT, DELETE, ...).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)
app.include_router(health_router)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(categories_router, prefix=settings.api_v1_prefix)
app.include_router(receipts_router, prefix=settings.api_v1_prefix)
app.include_router(transactions_router, prefix=settings.api_v1_prefix)
app.include_router(dashboard_router, prefix=settings.api_v1_prefix)

# Request → CORSMiddleware → RequestIdMiddleware → Endpoint
# Response ← CORSMiddleware ← RequestIdMiddleware ← Endpoint
