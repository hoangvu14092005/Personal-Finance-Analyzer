"""Schemas for data export/privacy APIs."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ExportStatus = Literal["queued", "ready", "failed"]


class DataExportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include_receipts: bool = True
    include_transactions: bool = True
    include_chat: bool = True


class DataExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    export_id: str
    status: ExportStatus
    created_at: datetime
    expires_at: datetime | None
    download_url: str | None = None
    message: str | None = None
    included: list[str] = Field(default_factory=list)


__all__ = ["DataExportCreate", "DataExportResponse", "ExportStatus"]
