"""Ephemeral data export request registry.

This is an API-contract MVP for the Settings data export UI. It keeps export
requests in memory and reports that file generation is not wired yet; no
financial/document source-of-truth data is modified here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.schemas.data_exports import DataExportCreate, DataExportResponse


@dataclass(frozen=True, slots=True)
class DataExportRecord:
    export_id: str
    user_id: int
    created_at: datetime
    expires_at: datetime
    included: list[str]


_EXPORTS: dict[str, DataExportRecord] = {}


def create_data_export(user_id: int, payload: DataExportCreate) -> DataExportResponse:
    included: list[str] = []
    if payload.include_transactions:
        included.append("transactions")
    if payload.include_receipts:
        included.append("receipts")
    if payload.include_chat:
        included.append("chat")

    now = datetime.now(tz=UTC)
    record = DataExportRecord(
        export_id=uuid4().hex,
        user_id=user_id,
        created_at=now,
        expires_at=now + timedelta(hours=1),
        included=included,
    )
    _EXPORTS[record.export_id] = record
    return data_export_response(record)


def get_data_export(user_id: int, export_id: str) -> DataExportResponse | None:
    record = _EXPORTS.get(export_id)
    if record is None or record.user_id != user_id:
        return None
    return data_export_response(record)


def data_export_response(record: DataExportRecord) -> DataExportResponse:
    return DataExportResponse(
        export_id=record.export_id,
        status="ready",
        created_at=record.created_at,
        expires_at=record.expires_at,
        download_url=None,
        message="Export request accepted; file generation pipeline is not enabled yet.",
        included=record.included,
    )


__all__ = ["create_data_export", "get_data_export"]
