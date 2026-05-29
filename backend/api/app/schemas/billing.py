"""Schemas for billing read APIs."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BillingPlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str
    name: str
    status: str
    currency: str
    monthly_price: str
    features: list[str]


class BillingUsageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_count: int = Field(ge=0)
    receipt_count: int = Field(ge=0)
    invoice_count: int = Field(ge=0)
    insight_count: int = Field(ge=0)
    storage_backend: str


class BillingHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[dict[str, str]]


class BillingCheckoutSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    checkout_url: str | None
    message: str


__all__ = [
    "BillingCheckoutSessionResponse",
    "BillingHistoryResponse",
    "BillingPlanResponse",
    "BillingUsageResponse",
]
