"""Schemas for merchant search APIs."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MerchantSearchItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merchant_id: int
    display_name: str
    normalized_name: str
    raw_name: str | None = None
    category_id: int | None = None
    confidence: float | None = None
    source: str | None = None
    last_used_at: datetime | None = None
    match_type: str = Field(pattern="^(alias|merchant)$")


class MerchantSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MerchantSearchItemResponse]


__all__ = ["MerchantSearchItemResponse", "MerchantSearchResponse"]
