from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pfa_shared.enums import ReceiptStatus
from sqlalchemy import Column, DateTime, Numeric, func
from sqlmodel import Field, SQLModel


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
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )


class Budget(SQLModel, table=True):
    __tablename__ = "budgets"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    category_id: int = Field(foreign_key="categories.id", index=True)
    period_month: str = Field(max_length=7, index=True)
    amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )


class InsightSnapshot(SQLModel, table=True):
    __tablename__ = "insight_snapshots"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    range_start: date = Field(index=True)
    range_end: date = Field(index=True)
    insights_json: str = Field(default="[]")
    recommendations_json: str = Field(default="[]")
    alerts_json: str = Field(default="[]")
    fingerprint: str = Field(max_length=128, index=True)
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
