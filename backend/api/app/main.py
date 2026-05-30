from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.v1.account import router as account_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.billing import router as billing_router
from app.api.v1.budgets import router as budgets_router
from app.api.v1.categories import router as categories_router
from app.api.v1.chat import router as chat_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.data import router as data_router
from app.api.v1.insights import router as insights_router
from app.api.v1.invoices import router as invoices_router
from app.api.v1.merchants import router as merchants_router
from app.api.v1.receipts import router as receipts_router
from app.api.v1.security import router as security_router
from app.api.v1.settings import router as settings_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.users import router as users_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.middleware.request_id import RequestIdMiddleware
from app.services.ocr_queue import shutdown_ocr_broker, startup_ocr_broker

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan: khởi động OCR broker khi app start, đóng khi shutdown.

    Schema được quản lý hoàn toàn bằng Alembic (source of truth). Trên DB mới
    phải chạy `alembic upgrade head` TRƯỚC khi start app — app không còn tự tạo
    bảng lúc startup (xem `backend/api/README.md`).

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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch all unhandled exceptions and return a 500 JSON response.

    CORS: chỉ phản chiếu `Origin` khi nó nằm trong whitelist
    `settings.parsed_cors_origins`, nhất quán với `CORSMiddleware`. Origin
    không hợp lệ (hoặc request không có Origin) sẽ KHÔNG được phản chiếu kèm
    credentials, tránh để origin trái phép đọc nội dung response lỗi.
    """
    logger.exception("Unhandled exception: %s", exc)

    headers: dict[str, str] = {}
    origin = request.headers.get("origin")
    if origin is not None and origin in settings.parsed_cors_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Vary"] = "Origin"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
        headers=headers,
    )


# CORS cho phép frontend từ domain khác gọi API.
# allow_origins: danh sách domain được phép gọi.
# allow_methods: chấp nhận tất cả HTTP methods (GET, POST, PUT, DELETE, ...).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)
app.include_router(health_router)
app.include_router(account_router, prefix=settings.api_v1_prefix)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(audit_router, prefix=settings.api_v1_prefix)
app.include_router(analytics_router, prefix=settings.api_v1_prefix)
app.include_router(categories_router, prefix=settings.api_v1_prefix)
app.include_router(billing_router, prefix=settings.api_v1_prefix)
app.include_router(data_router, prefix=settings.api_v1_prefix)
app.include_router(receipts_router, prefix=settings.api_v1_prefix)
app.include_router(transactions_router, prefix=settings.api_v1_prefix)
app.include_router(dashboard_router, prefix=settings.api_v1_prefix)
app.include_router(budgets_router, prefix=settings.api_v1_prefix)
app.include_router(chat_router, prefix=settings.api_v1_prefix)
app.include_router(insights_router, prefix=settings.api_v1_prefix)
app.include_router(invoices_router, prefix=settings.api_v1_prefix)
app.include_router(merchants_router, prefix=settings.api_v1_prefix)
app.include_router(security_router, prefix=settings.api_v1_prefix)
app.include_router(settings_router, prefix=settings.api_v1_prefix)
app.include_router(users_router, prefix=settings.api_v1_prefix)

# Request → CORSMiddleware → RequestIdMiddleware → Endpoint
# Response ← CORSMiddleware ← RequestIdMiddleware ← Endpoint
