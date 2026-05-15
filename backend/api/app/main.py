from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.budgets import router as budgets_router
from app.api.v1.categories import router as categories_router
from app.api.v1.chat import router as chat_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.receipts import router as receipts_router
from app.api.v1.transactions import router as transactions_router
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

    Khi Redis down, `startup_ocr_broker()` log warning và trả về False — app
    vẫn chạy được; `enqueue_ocr_job` sẽ fail-soft → endpoint upload rollback
    sang UPLOADED + error_code=queue_unavailable (xem `api/v1/receipts.py`).
    """
    # Ensure all tables exist (safe for production - uses IF NOT EXISTS)
    _ensure_tables()
    await startup_ocr_broker()
    try:
        yield
    finally:
        await shutdown_ocr_broker()


def _ensure_tables() -> None:
    """Create missing tables on startup. Safe to run multiple times."""
    from sqlalchemy import text
    from app.core.database import engine

    create_receipt_line_items_sql = """
    CREATE TABLE IF NOT EXISTS receipt_line_items (
        id SERIAL PRIMARY KEY,
        receipt_upload_id INTEGER NOT NULL REFERENCES receipt_uploads(id) ON DELETE CASCADE,
        line_number INTEGER NOT NULL DEFAULT 0,
        item_name VARCHAR(500) NOT NULL,
        quantity NUMERIC(10, 3) NOT NULL DEFAULT 1,
        unit_price NUMERIC(12, 2) NOT NULL,
        total_price NUMERIC(12, 2) NOT NULL,
        category_id INTEGER REFERENCES categories(id),
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS ix_receipt_line_items_receipt ON receipt_line_items(receipt_upload_id);
    CREATE INDEX IF NOT EXISTS ix_receipt_line_items_category ON receipt_line_items(category_id);
    """

    create_invoices_sql = """
    CREATE TABLE IF NOT EXISTS invoices (
        id SERIAL PRIMARY KEY,
        receipt_upload_id INTEGER NOT NULL UNIQUE REFERENCES receipt_uploads(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id),
        invoice_number VARCHAR(100),
        template_symbol VARCHAR(50),
        issue_date DATE,
        tax_lookup_code VARCHAR(100),
        currency VARCHAR(10) NOT NULL DEFAULT 'VND',
        seller_name VARCHAR(255),
        seller_tax_id VARCHAR(20),
        seller_address VARCHAR(500),
        buyer_name VARCHAR(255),
        buyer_tax_id VARCHAR(20),
        buyer_address VARCHAR(500),
        payment_method VARCHAR(100),
        subtotal_before_tax NUMERIC(15, 2),
        total_tax NUMERIC(15, 2),
        grand_total NUMERIC(15, 2),
        amount_in_words VARCHAR(500),
        digital_signature VARCHAR(500),
        signing_date DATE,
        lookup_link VARCHAR(500),
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS ix_invoices_receipt ON invoices(receipt_upload_id);
    CREATE INDEX IF NOT EXISTS ix_invoices_user ON invoices(user_id);
    """

    create_invoice_line_items_sql = """
    CREATE TABLE IF NOT EXISTS invoice_line_items (
        id SERIAL PRIMARY KEY,
        invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
        line_number INTEGER NOT NULL DEFAULT 0,
        item_name VARCHAR(500) NOT NULL,
        unit VARCHAR(50),
        quantity NUMERIC(10, 3) NOT NULL DEFAULT 1,
        unit_price NUMERIC(15, 2) NOT NULL,
        line_total NUMERIC(15, 2) NOT NULL,
        vat_rate NUMERIC(5, 2),
        vat_amount NUMERIC(15, 2),
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS ix_invoice_line_items_invoice ON invoice_line_items(invoice_id);
    """

    try:
        with engine.connect() as conn:
            conn.execute(text(create_receipt_line_items_sql))
            conn.execute(text(create_invoices_sql))
            conn.execute(text(create_invoice_line_items_sql))
            conn.commit()
        logger.info("Database tables ensured (receipt_line_items, invoices, invoice_line_items)")
    except Exception as exc:
        logger.warning("Failed to ensure tables: %s", exc)


app = FastAPI(
    title="Personal Finance Analyzer API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch all unhandled exceptions and return proper JSON response with CORS headers."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        },
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
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(categories_router, prefix=settings.api_v1_prefix)
app.include_router(receipts_router, prefix=settings.api_v1_prefix)
app.include_router(transactions_router, prefix=settings.api_v1_prefix)
app.include_router(dashboard_router, prefix=settings.api_v1_prefix)
app.include_router(budgets_router, prefix=settings.api_v1_prefix)
app.include_router(chat_router, prefix=settings.api_v1_prefix)

# Request → CORSMiddleware → RequestIdMiddleware → Endpoint
# Response ← CORSMiddleware ← RequestIdMiddleware ← Endpoint
