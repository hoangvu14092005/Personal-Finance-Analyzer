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
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, Text, UniqueConstraint, func
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
    account_deletion_requested_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    account_deletion_scheduled_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    account_deletion_cancelled_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )


class AuditLog(SQLModel, table=True):
    """User-owned audit event for security/account/settings actions."""

    __tablename__ = "audit_logs"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    actor_user_id: int = Field(foreign_key="users.id", index=True)
    event: str = Field(max_length=100, index=True)
    target_type: str | None = Field(default=None, max_length=100, index=True)
    target_id: str | None = Field(default=None, max_length=100, index=True)
    metadata_json: str = Field(
        default="{}",
        sa_column=Column(Text(), nullable=False),
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )


class UserSettings(SQLModel, table=True):
    """Per-user application settings.

    `users` keeps a small profile snapshot for compatibility/auth responses.
    This table is the settings source for UI/API preferences.
    """

    __tablename__ = "user_settings"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, unique=True)

    default_currency: str = Field(default="VND", max_length=10)
    timezone: str = Field(default="Asia/Ho_Chi_Minh", max_length=64)
    locale: str = Field(default="vi-VN", max_length=16)
    default_analytics_range: str = Field(default="30d", max_length=20)
    budget_month_start_day: int = Field(default=1, ge=1, le=28)
    number_format_locale: str = Field(default="vi-VN", max_length=16)
    show_decimals: bool = Field(default=False)

    allow_ai_data_processing: bool = Field(default=True)
    auto_generate_insights: bool = Field(default=True)
    assistant_use_history: bool = Field(default=True)
    email_notifications_enabled: bool = Field(default=True)
    push_notifications_enabled: bool = Field(default=False)
    budget_alerts_enabled: bool = Field(default=True)
    receipt_notifications_enabled: bool = Field(default=True)
    insight_notifications_enabled: bool = Field(default=True)
    receipt_file_retention_days: int = Field(default=365, ge=1)
    raw_prompt_retention_days: int = Field(default=90, ge=1)

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


class ReceiptUpload(SQLModel, table=True):
    __tablename__ = "receipt_uploads"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    file_name: str = Field(max_length=255)
    content_type: str = Field(max_length=100)
    file_size_bytes: int = Field(default=0)
    storage_key: str = Field(max_length=500)
    merchant_name: str | None = Field(default=None, max_length=255, index=True)
    receipt_date: date | None = Field(default=None, index=True)
    total_amount: Decimal | None = Field(default=None, sa_column=Column(Numeric(15, 2)))
    currency: str | None = Field(default=None, max_length=10)
    status: str = Field(default=ReceiptStatus.UPLOADED.value, max_length=50)
    ocr_status: str = Field(default="pending", max_length=50, index=True)
    has_invoice: bool = Field(default=False, index=True)
    error_code: str | None = Field(default=None, max_length=100)
    error_message: str | None = Field(default=None, max_length=500)
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


class Merchant(SQLModel, table=True):
    """Normalized merchant entity shared across users.

    `normalized_name` is deterministic and unique. User-specific OCR/manual aliases
    live in `UserMerchantAlias` so one merchant can have many raw names.
    """

    __tablename__ = "merchants"

    id: int | None = Field(default=None, primary_key=True)
    normalized_name: str = Field(index=True, unique=True, max_length=255)
    display_name: str = Field(max_length=255)
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


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    merchant_id: int | None = Field(default=None, foreign_key="merchants.id", index=True)
    category_id: int | None = Field(default=None, foreign_key="categories.id", index=True)
    receipt_upload_id: int | None = Field(
        default=None,
        foreign_key="receipt_uploads.id",
        index=True,
    )
    raw_merchant_name: str | None = Field(default=None, max_length=255)
    merchant_name: str | None = Field(default=None, max_length=255)
    amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    currency: str = Field(default="VND", max_length=10)
    transaction_date: date = Field(index=True)
    note: str | None = Field(default=None, max_length=1000)
    source: str = Field(default="manual", max_length=20)
    status: str = Field(default="confirmed", max_length=20, index=True)
    confirmed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
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
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
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


class Insight(SQLModel, table=True):
    """Row-level insight for feed/detail/dismiss/feedback flows."""

    __tablename__ = "insights"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    type: str = Field(max_length=50, index=True)
    severity: str = Field(default="info", max_length=20, index=True)
    title: str = Field(max_length=255)
    summary: str = Field(max_length=1000)
    evidence_json: str = Field(default="[]")
    actions_json: str = Field(default="[]")
    range_start: date = Field(index=True)
    range_end: date = Field(index=True)
    status: str = Field(default="active", max_length=20, index=True)
    dismissed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    expires_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    deleted_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
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


class InsightFeedback(SQLModel, table=True):
    """User feedback for a specific insight."""

    __tablename__ = "insight_feedback"

    id: int | None = Field(default=None, primary_key=True)
    insight_id: int = Field(foreign_key="insights.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    rating: str = Field(max_length=20)
    comment: str | None = Field(default=None, max_length=1000)
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


class UserMerchantAlias(SQLModel, table=True):
    """User-specific alias from raw merchant text to normalized merchant.

    This supersedes `UserMerchantMapping` while staying compatible with it during
    the migration period. The raw name is user-scoped because OCR/manual naming
    patterns are personal and may imply different preferred categories.
    """

    __tablename__ = "user_merchant_aliases"
    __table_args__ = (
        UniqueConstraint("user_id", "raw_name", name="uq_user_merchant_aliases_user_raw"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    raw_name: str = Field(max_length=255, index=True)
    normalized_name: str = Field(max_length=255, index=True)
    merchant_id: int = Field(foreign_key="merchants.id", index=True)
    category_id: int | None = Field(default=None, foreign_key="categories.id", index=True)
    confidence: float | None = Field(default=None)
    source: str = Field(default="manual", max_length=20)
    last_used_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )


class ChatConversation(SQLModel, table=True):
    """A user-owned chat thread for the assistant drawer/history UI."""

    __tablename__ = "chat_conversations"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    title: str | None = Field(default=None, max_length=255)
    archived_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    deleted_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
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


class ChatMessage(SQLModel, table=True):
    """Chat message entity (Phase 6 — AI Chatbot)."""

    __tablename__ = "chat_messages"

    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int | None = Field(
        default=None,
        foreign_key="chat_conversations.id",
        index=True,
    )
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
    transaction_id: int | None = Field(default=None, foreign_key="transactions.id", index=True)

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
    quantity: Decimal = Field(
        default=Decimal("1"),
        sa_column=Column(Numeric(10, 3), nullable=False),
    )
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
    user_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    receipt_upload_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("receipt_uploads.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    transaction_id: int | None = Field(default=None, foreign_key="transactions.id", index=True)
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
    "AuditLog",
    "Budget",
    "Category",
    "ChatConversation",
    "ChatMessage",
    "Insight",
    "InsightFeedback",
    "InsightSnapshot",
    "Invoice",
    "InvoiceLineItem",
    "Merchant",
    "OcrResult",
    "ReceiptLineItem",
    "ReceiptTextChunk",
    "ReceiptUpload",
    "Transaction",
    "User",
    "UserSettings",
    "UserMerchantAlias",
    "UserMerchantMapping",
]
