from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(..., gt=Decimal("0"), max_digits=12, decimal_places=2)
    currency: str = Field(default="VND", min_length=3, max_length=10)
    transaction_date: date
    merchant_name: str | None = Field(default=None, max_length=255)
    category_id: int | None = Field(default=None, gt=0)
    receipt_upload_id: int | None = Field(default=None, gt=0)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("merchant_name", "note")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class TransactionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=10)
    transaction_date: date | None = None
    merchant_name: str | None = Field(default=None, max_length=255)
    category_id: int | None = Field(default=None, gt=0)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class TransactionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    user_id: int
    category_id: int | None
    receipt_upload_id: int | None
    merchant_name: str | None
    amount: Decimal
    currency: str
    transaction_date: date
    note: str | None
    created_at: datetime


class TransactionListMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int
    page: int
    size: int


class TransactionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TransactionResponse]
    meta: TransactionListMeta
