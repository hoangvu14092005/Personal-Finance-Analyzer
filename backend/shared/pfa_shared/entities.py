"""SQLModel entities — single source of truth cho cả API và worker (M5).

Trước M5 entities sống ở `app/models/entities.py` (chỉ API truy cập); worker
dùng raw SQL thông qua `sqlalchemy.text()`. Khi move sang đây cả 2 service
chia sẻ cùng SQLModel definitions → dễ refactor + đỡ drift schema.

Migration mapping (Alembic) vẫn ở `backend/api/alembic/versions/` vì API là
service "owner" của schema migrations.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlmodel import Field, SQLModel

from pfa_shared.enums import ReceiptStatus

# Embedding dimension cho sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2.
# Lock const để tránh mismatch giữa entity và embedding client.
EMBEDDING_DIMENSION = 384


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=255)
    password_hash: str = Field(max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    currency: str = Field(default="VND", max_length=10)
    timezone: str = Field(default="Asia/Ho_Chi_Minh", max_length=64)
    locale: str = Field(default="vi-VN", max_length=16)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )


class ReceiptUpload(SQLModel, table=True):
    __tablename__ = "receipt_uploads"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    file_name: str = Field(max_length=255)
    content_type: str = Field(max_length=100)
    file_size_bytes: int = Field(default=0)
    storage_key: str = Field(max_length=500)
    status: str = Field(default=ReceiptStatus.UPLOADED.value, max_length=50)
    error_code: str | None = Field(default=None, max_length=100)
    error_message: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )


class OcrResult(SQLModel, table=True):
    __tablename__ = "ocr_results"

    id: int | None = Field(default=None, primary_key=True)
    receipt_upload_id: int = Field(foreign_key="receipt_uploads.id", unique=True)
    provider: str = Field(max_length=100)
    raw_text: str | None = Field(default=None)
    confidence: float | None = Field(default=None)
    normalized_payload: str | None = Field(default=None)
    status: str = Field(default=ReceiptStatus.READY.value, max_length=50)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )


class Category(SQLModel, table=True):
    __tablename__ = "categories"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    name: str = Field(max_length=100, index=True)
    color: str | None = Field(default=None, max_length=20)
    is_system: bool = Field(default=False, index=True)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    category_id: int | None = Field(default=None, foreign_key="categories.id", index=True)
    receipt_upload_id: int | None = Field(
        default=None,
        foreign_key="receipt_uploads.id",
        index=True,
    )
    merchant_name: str | None = Field(default=None, max_length=255)
    amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    currency: str = Field(default="VND", max_length=10)
    transaction_date: date = Field(index=True)
    note: str | None = Field(default=None, max_length=1000)
    # Embedding của "merchant_name + note" để semantic_search_transactions (Phase 7).
    # Nullable để transactions cũ chưa index vẫn tồn tại. Script backfill sẽ fill sau.
    search_embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(EMBEDDING_DIMENSION), nullable=True),
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )


class Budget(SQLModel, table=True):
    __tablename__ = "budgets"
    # Một user chỉ có 1 budget duy nhất cho cặp (category, period_month).
    # Tránh duplicate → dashboard aggregation deterministic.
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "category_id",
            "period_month",
            name="uq_budgets_user_category_period",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    category_id: int = Field(foreign_key="categories.id", index=True)
    # Format "YYYY-MM" (max 7 chars). Validate ở Pydantic schema.
    period_month: str = Field(max_length=7, index=True)
    amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        ),
    )


class InsightSnapshot(SQLModel, table=True):
    __tablename__ = "insight_snapshots"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    # Phase 6 — preset để query "latest của user + preset" dễ hơn.
    range_preset: str = Field(default="custom", max_length=20, index=True)
    range_start: date = Field(index=True)
    range_end: date = Field(index=True)
    # Provider nào sinh ra payload (mock/ollama/gemini/...). Để audit.
    provider: str = Field(default="mock", max_length=50)
    insights_json: str = Field(default="[]")
    recommendations_json: str = Field(default="[]")
    alerts_json: str = Field(default="[]")
    # SHA256 hex (64 chars). Cache lookup: (user_id, fingerprint) → snapshot.
    fingerprint: str = Field(max_length=128, index=True)
    # Eligibility fail hoặc lỗi → status != "ready". UI fallback.
    status: str = Field(default="ready", max_length=20)
    # Nếu status=insufficient_data/failed → chứa lý do để UI hiển thị.
    status_reason: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )


class UserMerchantMapping(SQLModel, table=True):
    __tablename__ = "user_merchant_mappings"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    raw_merchant_name: str = Field(max_length=255, index=True)
    normalized_merchant_name: str = Field(max_length=255)
    category_id: int | None = Field(default=None, foreign_key="categories.id", index=True)
    confidence: float | None = Field(default=None)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )


class ChatMessage(SQLModel, table=True):
    """Chat message entity (Phase 6 — AI Chatbot)."""

    __tablename__ = "chat_messages"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    role: str = Field(max_length=20)  # "user" | "assistant" | "tool"
    content: str | None = Field(default=None)
    tool_calls_json: str | None = Field(default=None)
    tool_call_id: str | None = Field(default=None, max_length=100)
    tool_name: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )


class ReceiptTextChunk(SQLModel, table=True):
    """Receipt OCR text chunk với embedding (Phase 7 — RAG).

    Mỗi receipt sau khi OCR xong được split thành chunks (nếu text > 500 chars)
    và embed để chatbot tool `search_receipt_text` tìm được nội dung chi tiết.
    """

    __tablename__ = "receipt_text_chunks"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    # CASCADE delete: khi receipt bị xóa, chunks cũng xóa theo.
    receipt_upload_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("receipt_uploads.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    chunk_text: str
    chunk_index: int = Field(default=0)
    embedding: list[float] = Field(
        sa_column=Column(Vector(EMBEDDING_DIMENSION), nullable=False),
    )
    source_type: str = Field(default="receipt_ocr", max_length=32)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )


class Invoice(SQLModel, table=True):
    """Full Vietnamese e-invoice entity (hóa đơn điện tử).

    Liên kết 1-1 với ReceiptUpload. Lưu toàn bộ thông tin hóa đơn bao gồm:
    metadata, seller, buyer, totals, authentication/digital signature.
    """

    __tablename__ = "invoices"

    id: int | None = Field(default=None, primary_key=True)
    receipt_upload_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("receipt_uploads.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
    )
    user_id: int = Field(foreign_key="users.id", index=True)

    # Invoice metadata
    invoice_number: str | None = Field(default=None, max_length=100)
    template_symbol: str | None = Field(default=None, max_length=50)
    issue_date: date | None = Field(default=None)
    tax_lookup_code: str | None = Field(default=None, max_length=100)
    currency: str = Field(default="VND", max_length=10)

    # Seller info
    seller_name: str | None = Field(default=None, max_length=255)
    seller_tax_id: str | None = Field(default=None, max_length=20)
    seller_address: str | None = Field(default=None, max_length=500)

    # Buyer info
    buyer_name: str | None = Field(default=None, max_length=255)
    buyer_tax_id: str | None = Field(default=None, max_length=20)
    buyer_address: str | None = Field(default=None, max_length=500)
    payment_method: str | None = Field(default=None, max_length=100)

    # Totals
    subtotal_before_tax: Decimal | None = Field(default=None, sa_column=Column(Numeric(15, 2)))
    total_tax: Decimal | None = Field(default=None, sa_column=Column(Numeric(15, 2)))
    grand_total: Decimal | None = Field(default=None, sa_column=Column(Numeric(15, 2)))
    amount_in_words: str | None = Field(default=None, max_length=500)

    # Authentication / digital signature
    digital_signature: str | None = Field(default=None, max_length=500)
    signing_date: date | None = Field(default=None)
    lookup_link: str | None = Field(default=None, max_length=500)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )


class InvoiceLineItem(SQLModel, table=True):
    """Line item from Vietnamese e-invoice with VAT info.

    Mỗi Invoice có nhiều InvoiceLineItem. CASCADE delete khi Invoice bị xóa.
    """

    __tablename__ = "invoice_line_items"

    id: int | None = Field(default=None, primary_key=True)
    invoice_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    line_number: int = Field(default=0)
    item_name: str = Field(max_length=500)
    unit: str | None = Field(default=None, max_length=50)
    quantity: Decimal = Field(default=Decimal("1"), sa_column=Column(Numeric(10, 3), nullable=False))
    unit_price: Decimal = Field(sa_column=Column(Numeric(15, 2), nullable=False))
    line_total: Decimal = Field(sa_column=Column(Numeric(15, 2), nullable=False))

    # VAT
    vat_rate: Decimal | None = Field(default=None, sa_column=Column(Numeric(5, 2)))
    vat_amount: Decimal | None = Field(default=None, sa_column=Column(Numeric(15, 2)))

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )


class ReceiptLineItem(SQLModel, table=True):
    """Line items extracted from receipt OCR.
    
    Mỗi hóa đơn có thể có nhiều line items (sản phẩm/dịch vụ).
    Tổng của tất cả line items nên bằng total_amount trong OcrResult.
    """

    __tablename__ = "receipt_line_items"

    id: int | None = Field(default=None, primary_key=True)
    receipt_upload_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("receipt_uploads.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    line_number: int = Field(default=0)  # Thứ tự trong hóa đơn (0-indexed)
    item_name: str = Field(max_length=500)
    quantity: Decimal = Field(
        default=Decimal("1"),
        sa_column=Column(Numeric(10, 3), nullable=False),
    )
    unit_price: Decimal = Field(
        sa_column=Column(Numeric(12, 2), nullable=False),
    )
    total_price: Decimal = Field(
        sa_column=Column(Numeric(12, 2), nullable=False),
    )
    # Category suggestion cho từng line item (optional)
    category_id: int | None = Field(default=None, foreign_key="categories.id")
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )


__all__ = [
    "EMBEDDING_DIMENSION",
    "Budget",
    "Category",
    "ChatMessage",
    "InsightSnapshot",
    "Invoice",
    "InvoiceLineItem",
    "OcrResult",
    "ReceiptLineItem",
    "ReceiptTextChunk",
    "ReceiptUpload",
    "Transaction",
    "User",
    "UserMerchantMapping",
]
