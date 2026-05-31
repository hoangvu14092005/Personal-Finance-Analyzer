"""Data export generation (G1 — real file pipeline).

Sinh file ZIP thật chứa dữ liệu user (transactions/receipts/chat) dưới dạng
CSV + JSON, upload lên storage tại `exports/{user_id}/{export_id}.zip`, và phục
vụ tải về qua endpoint download.

Thiết kế:
- Export sinh đồng bộ ngay khi request (dữ liệu tài chính cá nhân nhỏ, không cần
  job nền). Nếu sau này dữ liệu lớn có thể chuyển sang worker.
- `storage_key` nhúng `user_id` nên endpoint download xác thực được quyền sở hữu
  mà không phụ thuộc registry in-memory (bền vững qua restart API).
- Registry in-memory chỉ phục vụ poll status; download đọc thẳng từ storage.
- KHÔNG sửa nguồn sự thật tài chính/tài liệu — chỉ đọc.
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlmodel import Session, col, select

from app.integrations.storage import StorageNotFoundError, get_storage_service
from app.models.entities import (
    Category,
    ChatConversation,
    ChatMessage,
    Invoice,
    InvoiceLineItem,
    ReceiptLineItem,
    ReceiptUpload,
    Transaction,
)
from app.schemas.data_exports import DataExportCreate, DataExportResponse

EXPORT_TTL_HOURS = 24


@dataclass(frozen=True, slots=True)
class DataExportRecord:
    export_id: str
    user_id: int
    created_at: datetime
    expires_at: datetime
    included: list[str]
    storage_key: str
    size_bytes: int


_EXPORTS: dict[str, DataExportRecord] = {}


def _export_storage_key(user_id: int, export_id: str) -> str:
    return f"exports/{user_id}/{export_id}.zip"


def _write_csv(rows: list[dict[str, object]], fieldnames: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def _collect_transactions(session: Session, user_id: int) -> str:
    # Map category_id -> name (system + user categories) để export đọc được.
    category_names: dict[int, str] = {}
    for cat in session.exec(
        select(Category).where(
            (col(Category.user_id) == user_id) | col(Category.is_system).is_(True),
        ),
    ):
        if cat.id is not None:
            category_names[cat.id] = cat.name

    rows: list[dict[str, object]] = []
    statement = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(col(Transaction.transaction_date).desc(), col(Transaction.id).desc())
    )
    for tx in session.exec(statement):
        rows.append(
            {
                "id": tx.id,
                "transaction_date": tx.transaction_date.isoformat(),
                "merchant_name": tx.merchant_name or tx.raw_merchant_name or "",
                "category": category_names.get(tx.category_id, "") if tx.category_id else "",
                "amount": str(tx.amount),
                "currency": tx.currency,
                "note": tx.note or "",
                "source": tx.source,
                "status": tx.status,
                "receipt_upload_id": tx.receipt_upload_id or "",
            },
        )
    return _write_csv(
        rows,
        [
            "id", "transaction_date", "merchant_name", "category", "amount",
            "currency", "note", "source", "status", "receipt_upload_id",
        ],
    )


def _collect_receipts(session: Session, user_id: int) -> str:
    rows: list[dict[str, object]] = []
    statement = (
        select(ReceiptUpload)
        .where(ReceiptUpload.user_id == user_id)
        .order_by(col(ReceiptUpload.created_at).desc())
    )
    for r in session.exec(statement):
        rows.append(
            {
                "id": r.id,
                "file_name": r.file_name,
                "merchant_name": r.merchant_name or "",
                "receipt_date": r.receipt_date.isoformat() if r.receipt_date else "",
                "total_amount": str(r.total_amount) if r.total_amount is not None else "",
                "currency": r.currency or "",
                "status": r.status,
                "ocr_status": r.ocr_status,
                "has_invoice": r.has_invoice,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            },
        )
    return _write_csv(
        rows,
        [
            "id", "file_name", "merchant_name", "receipt_date", "total_amount",
            "currency", "status", "ocr_status", "has_invoice", "created_at",
        ],
    )


def _collect_receipt_line_items(session: Session, user_id: int) -> str:
    rows: list[dict[str, object]] = []
    statement = (
        select(ReceiptLineItem)
        .where(ReceiptLineItem.user_id == user_id)
        .order_by(
            col(ReceiptLineItem.receipt_upload_id).asc(),
            col(ReceiptLineItem.line_number).asc(),
        )
    )
    for li in session.exec(statement):
        rows.append(
            {
                "receipt_upload_id": li.receipt_upload_id,
                "line_number": li.line_number,
                "item_name": li.item_name,
                "quantity": str(li.quantity),
                "unit_price": str(li.unit_price),
                "total_price": str(li.total_price),
            },
        )
    return _write_csv(
        rows,
        ["receipt_upload_id", "line_number", "item_name", "quantity", "unit_price", "total_price"],
    )


def _collect_invoices(session: Session, user_id: int) -> str:
    invoices = list(
        session.exec(
            select(Invoice)
            .where(Invoice.user_id == user_id)
            .order_by(col(Invoice.id).asc()),
        ),
    )
    payload: list[dict[str, object]] = []
    for inv in invoices:
        line_items = session.exec(
            select(InvoiceLineItem)
            .where(InvoiceLineItem.invoice_id == inv.id)
            .order_by(col(InvoiceLineItem.line_number).asc()),
        ).all()
        payload.append(
            {
                "id": inv.id,
                "receipt_upload_id": inv.receipt_upload_id,
                "invoice_number": inv.invoice_number,
                "template_symbol": inv.template_symbol,
                "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
                "currency": inv.currency,
                "seller_name": inv.seller_name,
                "seller_tax_id": inv.seller_tax_id,
                "buyer_name": inv.buyer_name,
                "buyer_tax_id": inv.buyer_tax_id,
                "subtotal_before_tax": (
                    str(inv.subtotal_before_tax) if inv.subtotal_before_tax is not None else None
                ),
                "total_tax": str(inv.total_tax) if inv.total_tax is not None else None,
                "grand_total": str(inv.grand_total) if inv.grand_total is not None else None,
                "line_items": [
                    {
                        "line_number": li.line_number,
                        "item_name": li.item_name,
                        "unit": li.unit,
                        "quantity": str(li.quantity),
                        "unit_price": str(li.unit_price),
                        "line_total": str(li.line_total),
                        "vat_rate": str(li.vat_rate) if li.vat_rate is not None else None,
                        "vat_amount": str(li.vat_amount) if li.vat_amount is not None else None,
                    }
                    for li in line_items
                ],
            },
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _collect_chat(session: Session, user_id: int) -> str:
    conversations = list(
        session.exec(
            select(ChatConversation)
            .where(ChatConversation.user_id == user_id)
            .where(col(ChatConversation.deleted_at).is_(None))
            .order_by(col(ChatConversation.created_at).asc()),
        ),
    )
    payload: list[dict[str, object]] = []
    for conv in conversations:
        messages = session.exec(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conv.id)
            .order_by(col(ChatMessage.created_at).asc(), col(ChatMessage.id).asc()),
        ).all()
        payload.append(
            {
                "conversation_id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "messages": [
                    {
                        "role": m.role,
                        "content": m.content,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                    }
                    for m in messages
                    if m.role in {"user", "assistant"}
                ],
            },
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _build_zip(
    session: Session,
    user_id: int,
    payload: DataExportCreate,
    included: list[str],
) -> bytes:
    buffer = io.BytesIO()
    now = datetime.now(tz=UTC)
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if payload.include_transactions:
            zf.writestr("transactions.csv", _collect_transactions(session, user_id))
        if payload.include_receipts:
            zf.writestr("receipts.csv", _collect_receipts(session, user_id))
            zf.writestr("receipt_line_items.csv", _collect_receipt_line_items(session, user_id))
            zf.writestr("invoices.json", _collect_invoices(session, user_id))
        if payload.include_chat:
            zf.writestr("chat.json", _collect_chat(session, user_id))

        manifest = {
            "generated_at": now.isoformat(),
            "user_id": user_id,
            "included": included,
            "format": "Personal Finance Analyzer data export v1",
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return buffer.getvalue()


def create_data_export(
    session: Session,
    user_id: int,
    payload: DataExportCreate,
) -> DataExportResponse:
    included: list[str] = []
    if payload.include_transactions:
        included.append("transactions")
    if payload.include_receipts:
        included.append("receipts")
    if payload.include_chat:
        included.append("chat")

    export_id = uuid4().hex
    archive = _build_zip(session, user_id, payload, included)
    storage_key = _export_storage_key(user_id, export_id)
    get_storage_service().upload_bytes(storage_key, archive, "application/zip")

    now = datetime.now(tz=UTC)
    record = DataExportRecord(
        export_id=export_id,
        user_id=user_id,
        created_at=now,
        expires_at=now + timedelta(hours=EXPORT_TTL_HOURS),
        included=included,
        storage_key=storage_key,
        size_bytes=len(archive),
    )
    _EXPORTS[export_id] = record
    return data_export_response(record)


def get_data_export(user_id: int, export_id: str) -> DataExportResponse | None:
    record = _EXPORTS.get(export_id)
    if record is None or record.user_id != user_id:
        return None
    return data_export_response(record)


def load_export_archive(user_id: int, export_id: str) -> bytes | None:
    """Tải bytes ZIP từ storage. Trả None nếu không tồn tại / hết hạn.

    Không phụ thuộc registry: dựng storage_key từ user_id (đã xác thực) +
    export_id nên vẫn hoạt động sau khi API restart.
    """
    storage_key = _export_storage_key(user_id, export_id)
    try:
        return get_storage_service().download_bytes(storage_key)
    except StorageNotFoundError:
        return None


def data_export_response(record: DataExportRecord) -> DataExportResponse:
    return DataExportResponse(
        export_id=record.export_id,
        status="ready",
        created_at=record.created_at,
        expires_at=record.expires_at,
        download_url=f"/api/v1/data/export/{record.export_id}/download",
        message="Export ready. Use the download link to retrieve your ZIP archive.",
        included=record.included,
    )


__all__ = ["create_data_export", "get_data_export", "load_export_archive"]
