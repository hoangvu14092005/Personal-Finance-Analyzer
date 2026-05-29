"""Schemas for row-level Insights APIs."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

InsightSeverity = Literal["info", "success", "watch", "warning", "danger"]
InsightStatus = Literal["active", "dismissed", "expired"]
FeedbackRating = Literal["helpful", "not_helpful", "irrelevant"]


class InsightResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    type: str
    severity: InsightSeverity
    title: str
    summary: str
    evidence: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    range_start: date
    range_end: date
    status: InsightStatus
    dismissed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InsightListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[InsightResponse]
    has_more: bool
    next_before_id: int | None = None


class InsightUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["active", "dismissed"]


class InsightFeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: FeedbackRating
    comment: str | None = Field(default=None, max_length=1000)


class InsightFeedbackResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    insight_id: int
    rating: FeedbackRating
    comment: str | None
    created_at: datetime


class InsightGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    range: Literal["7d", "30d", "this_month", "last_month", "custom"] = "30d"
    start_date: date | None = None
    end_date: date | None = None
    force_refresh: bool = False
    types: list[str] | None = None


class InsightGenerateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[InsightResponse]
    generated_count: int = Field(ge=0)


__all__ = [
    "FeedbackRating",
    "InsightFeedbackCreate",
    "InsightFeedbackResponse",
    "InsightGenerateRequest",
    "InsightGenerateResponse",
    "InsightListResponse",
    "InsightResponse",
    "InsightSeverity",
    "InsightStatus",
    "InsightUpdate",
]
