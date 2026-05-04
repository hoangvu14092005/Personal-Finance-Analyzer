"""Pydantic schemas cho Budget CRUD + Usage (Phase 5).

`period_month` format: "YYYY-MM" (ISO 8601 year-month, max 7 chars).
Status enum: "safe" | "warning" | "exceeded" (xem `services/budgets.py`).
"""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# "YYYY-MM" — 4 số năm + "-" + 2 số tháng (01-12).
_PERIOD_MONTH_PATTERN = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def _validate_period_month(value: str) -> str:
    """Raise ValueError nếu không match "YYYY-MM" format hợp lệ."""
    value = value.strip()
    if not _PERIOD_MONTH_PATTERN.match(value):
        raise ValueError(
            "period_month phải có dạng YYYY-MM (vd: 2026-05), "
            "tháng từ 01 tới 12."
        )
    return value


class BudgetCreate(BaseModel):
    """Payload POST /budgets."""

    model_config = ConfigDict(extra="forbid")

    category_id: int = Field(..., gt=0)
    period_month: str = Field(..., min_length=7, max_length=7)
    amount: Decimal = Field(
        ...,
        gt=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        description="Số tiền ngân sách (> 0). VND không có fractional phần.",
    )

    @field_validator("period_month")
    @classmethod
    def validate_period_month(cls, value: str) -> str:
        return _validate_period_month(value)


class BudgetUpdate(BaseModel):
    """Payload PUT /budgets/{id}. Chỉ cho update `amount` — không cho đổi
    `category_id` hoặc `period_month` (tránh phá unique constraint; user nên
    delete + create mới)."""

    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(
        ...,
        gt=Decimal("0"),
        max_digits=12,
        decimal_places=2,
    )


class BudgetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    user_id: int
    category_id: int
    period_month: str
    amount: Decimal
    created_at: datetime
    updated_at: datetime


class BudgetListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[BudgetResponse]


# === Usage schemas (P5.3, P5.4) ===


BudgetStatus = Literal["safe", "warning", "exceeded"]


class BudgetUsageResponse(BaseModel):
    """Một dòng usage cho 1 budget trong 1 period."""

    model_config = ConfigDict(extra="forbid")

    budget_id: int
    category_id: int
    category_name: str
    category_color: str | None
    period_month: str
    budget_amount: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    percent_used: float = Field(
        ge=0,
        description="Phần trăm dùng (clamped 0..inf). 100 = vừa hết budget.",
    )
    status: BudgetStatus


__all__ = [
    "BudgetCreate",
    "BudgetListResponse",
    "BudgetResponse",
    "BudgetStatus",
    "BudgetUpdate",
    "BudgetUsageResponse",
]
