"""Account purge job (G1).

Khi user yêu cầu xóa tài khoản (`/account/delete-request`), hệ thống set
`account_deletion_scheduled_at = now + grace_period`. Tài khoản vào trạng thái
"pending deletion" (auth chặn đăng nhập) nhưng dữ liệu CHƯA bị xóa để user còn
kịp hủy trong grace period.

Job này quét các tài khoản đã quá hạn (scheduled_at <= now, chưa hủy) và xóa
vĩnh viễn toàn bộ dữ liệu thuộc về user theo thứ tự FK an toàn, đồng thời xóa
file receipt + file export trên storage.

Chạy:
- Định kỳ qua cron/Task Scheduler: `python run_account_purge.py`
- Hoặc enqueue task `purge_due_accounts_task` từ scheduler ngoài.

An toàn:
- Chỉ xử lý user có scheduled_at <= now VÀ cancelled_at IS NULL.
- Merchants là dữ liệu global dùng chung → KHÔNG xóa.
- Idempotent: chạy lại không lỗi (user đã xóa thì không còn trong kết quả query).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from pfa_shared.entities import (
    AuditLog,
    Budget,
    Category,
    ChatConversation,
    ChatMessage,
    Insight,
    InsightFeedback,
    InsightSnapshot,
    Invoice,
    InvoiceLineItem,
    OcrResult,
    ReceiptLineItem,
    ReceiptTextChunk,
    ReceiptUpload,
    Transaction,
    User,
    UserMerchantAlias,
    UserMerchantMapping,
    UserSettings,
)
from pfa_shared.logging import get_logger
from pfa_shared.storage import StorageService, build_storage_service
from sqlmodel import Session, col, delete, select

from worker_app import broker, engine, settings

logger = get_logger("worker.purge")


@dataclass(frozen=True, slots=True)
class PurgeResult:
    purged_user_ids: list[int]
    storage_keys_deleted: int
    storage_errors: int


def find_due_user_ids(session: Session, *, now: datetime) -> list[int]:
    """Trả id các user đã quá grace period và chưa hủy yêu cầu xóa."""
    statement = (
        select(User.id)
        .where(col(User.account_deletion_scheduled_at).is_not(None))
        .where(User.account_deletion_scheduled_at <= now)  # type: ignore[operator]
        .where(col(User.account_deletion_cancelled_at).is_(None))
    )
    return [uid for uid in session.exec(statement).all() if uid is not None]


def _collect_storage_keys(session: Session, user_id: int) -> list[str]:
    """Thu thập storage_key của receipt files để xóa sau khi xóa DB rows."""
    keys = session.exec(
        select(ReceiptUpload.storage_key).where(ReceiptUpload.user_id == user_id),
    ).all()
    return [k for k in keys if k]


def _delete_user_rows(session: Session, user_id: int) -> None:
    """Xóa toàn bộ DB rows thuộc về user theo thứ tự FK an toàn (con trước cha)."""
    # Ids trung gian cho bảng không có cột user_id trực tiếp.
    receipt_ids = [
        r for r in session.exec(
            select(ReceiptUpload.id).where(ReceiptUpload.user_id == user_id),
        ).all() if r is not None
    ]
    invoice_ids = [
        i for i in session.exec(
            select(Invoice.id).where(Invoice.user_id == user_id),
        ).all() if i is not None
    ]

    # 1. Insight feedback -> insights -> snapshots
    session.exec(delete(InsightFeedback).where(InsightFeedback.user_id == user_id))  # type: ignore[arg-type]
    session.exec(delete(Insight).where(Insight.user_id == user_id))  # type: ignore[arg-type]
    session.exec(delete(InsightSnapshot).where(InsightSnapshot.user_id == user_id))  # type: ignore[arg-type]

    # 2. Chat messages -> conversations
    session.exec(delete(ChatMessage).where(ChatMessage.user_id == user_id))  # type: ignore[arg-type]
    session.exec(delete(ChatConversation).where(ChatConversation.user_id == user_id))  # type: ignore[arg-type]

    # 3. RAG chunks
    session.exec(delete(ReceiptTextChunk).where(ReceiptTextChunk.user_id == user_id))  # type: ignore[arg-type]

    # 4. Invoice line items -> invoices (line items chỉ có invoice_id)
    if invoice_ids:
        session.exec(
            delete(InvoiceLineItem).where(col(InvoiceLineItem.invoice_id).in_(invoice_ids)),  # type: ignore[arg-type]
        )
    session.exec(delete(Invoice).where(Invoice.user_id == user_id))  # type: ignore[arg-type]

    # 5. Receipt line items (ref transactions + receipts)
    session.exec(delete(ReceiptLineItem).where(ReceiptLineItem.user_id == user_id))  # type: ignore[arg-type]

    # 6. Transactions (ref receipts/categories/merchants)
    session.exec(delete(Transaction).where(Transaction.user_id == user_id))  # type: ignore[arg-type]

    # 7. OCR results (chỉ có receipt_upload_id, no user_id) -> trước receipt_uploads
    if receipt_ids:
        session.exec(
            delete(OcrResult).where(col(OcrResult.receipt_upload_id).in_(receipt_ids)),  # type: ignore[arg-type]
        )

    # 8. Receipt uploads
    session.exec(delete(ReceiptUpload).where(ReceiptUpload.user_id == user_id))  # type: ignore[arg-type]

    # 9. Budgets (ref categories)
    session.exec(delete(Budget).where(Budget.user_id == user_id))  # type: ignore[arg-type]

    # 10. Merchant aliases + legacy mappings (ref categories)
    session.exec(delete(UserMerchantAlias).where(UserMerchantAlias.user_id == user_id))  # type: ignore[arg-type]
    session.exec(delete(UserMerchantMapping).where(UserMerchantMapping.user_id == user_id))  # type: ignore[arg-type]

    # 11. Categories (user-owned only; system categories user_id IS NULL)
    session.exec(delete(Category).where(Category.user_id == user_id))  # type: ignore[arg-type]

    # 12. Settings
    session.exec(delete(UserSettings).where(UserSettings.user_id == user_id))  # type: ignore[arg-type]

    # 13. Audit logs (ref users qua user_id + actor_user_id)
    session.exec(delete(AuditLog).where(AuditLog.user_id == user_id))  # type: ignore[arg-type]
    session.exec(delete(AuditLog).where(AuditLog.actor_user_id == user_id))  # type: ignore[arg-type]

    # 14. User
    session.exec(delete(User).where(User.id == user_id))  # type: ignore[arg-type]


def purge_account(
    session: Session,
    storage: StorageService,
    user_id: int,
) -> int:
    """Xóa toàn bộ dữ liệu của 1 user + file storage. Trả số file đã xóa.

    DB rows commit trong 1 transaction. File storage xóa best-effort sau commit
    (file mồ côi không gây hỏng dữ liệu, có thể dọn lại sau).
    """
    storage_keys = _collect_storage_keys(session, user_id)
    _delete_user_rows(session, user_id)
    session.commit()

    deleted = 0
    for key in storage_keys:
        try:
            storage.delete(key)
            deleted += 1
        except Exception:  # noqa: BLE001 - storage cleanup best-effort
            logger.warning("purge.storage_delete_failed user_id=%d key=%s", user_id, key)
    return deleted


def run_purge_due_accounts(
    session: Session,
    storage: StorageService,
    *,
    now: datetime | None = None,
) -> PurgeResult:
    """Core purge logic — testable. Xóa tất cả tài khoản đã quá grace period."""
    effective_now = now or datetime.now(tz=UTC)
    user_ids = find_due_user_ids(session, now=effective_now)

    purged: list[int] = []
    total_deleted = 0
    errors = 0
    for uid in user_ids:
        try:
            total_deleted += purge_account(session, storage, uid)
            purged.append(uid)
            logger.info("purge.account_purged user_id=%d", uid)
        except Exception:
            session.rollback()
            errors += 1
            logger.exception("purge.account_failed user_id=%d", uid)

    return PurgeResult(
        purged_user_ids=purged,
        storage_keys_deleted=total_deleted,
        storage_errors=errors,
    )


@broker.task
async def purge_due_accounts_task() -> str:
    """TaskIQ entry: purge các tài khoản đã quá grace period."""
    storage = build_storage_service(settings)
    with Session(engine) as session:
        result = run_purge_due_accounts(session, storage)
    return (
        f"purged={len(result.purged_user_ids)} "
        f"files={result.storage_keys_deleted} "
        f"errors={result.storage_errors}"
    )


__all__ = [
    "PurgeResult",
    "find_due_user_ids",
    "purge_account",
    "purge_due_accounts_task",
    "run_purge_due_accounts",
]
