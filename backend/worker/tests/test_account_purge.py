"""Tests cho account purge job (G1).

SQLite in-memory + LocalStorage tmp dir. Verify:
- Chỉ purge user đã quá grace period (scheduled_at <= now, chưa hủy).
- User chưa tới hạn / đã hủy yêu cầu xóa KHÔNG bị purge.
- Purge xóa toàn bộ dữ liệu user (transactions/receipts/budgets/...) + file storage.
- Dữ liệu user khác KHÔNG bị ảnh hưởng. System categories KHÔNG bị xóa.
- Idempotent: chạy lại không lỗi.
"""
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from pfa_shared.entities import (
    Budget,
    Category,
    OcrResult,
    ReceiptUpload,
    Transaction,
    User,
)
from pfa_shared.storage.local import LocalStorageService
from sqlmodel import Session, SQLModel, create_engine, select

from account_purge import find_due_user_ids, run_purge_due_accounts


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorageService:
    return LocalStorageService(root_dir=tmp_path)


def _seed_user(
    session: Session,
    email: str,
    *,
    scheduled_at: datetime | None = None,
    cancelled_at: datetime | None = None,
) -> User:
    user = User(
        email=email,
        password_hash="x",
        account_deletion_requested_at=scheduled_at,
        account_deletion_scheduled_at=scheduled_at,
        account_deletion_cancelled_at=cancelled_at,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    assert user.id is not None
    return user


def _seed_user_data(
    session: Session,
    storage: LocalStorageService,
    user_id: int,
) -> str:
    """Seed category + budget + receipt(file) + ocr + transaction. Trả storage_key."""
    category = Category(user_id=user_id, name="Custom", is_system=False)
    session.add(category)
    session.commit()
    session.refresh(category)

    storage_key = f"{user_id}/receipt.jpg"
    storage.upload_bytes(storage_key, b"fake", "image/jpeg")
    receipt = ReceiptUpload(
        user_id=user_id,
        file_name="receipt.jpg",
        content_type="image/jpeg",
        file_size_bytes=4,
        storage_key=storage_key,
    )
    session.add(receipt)
    session.commit()
    session.refresh(receipt)
    assert receipt.id is not None

    session.add(OcrResult(receipt_upload_id=receipt.id, provider="mock", raw_text="x"))
    session.add(
        Budget(
            user_id=user_id,
            category_id=category.id,
            period_month="2026-05",
            amount=Decimal("100000"),
        ),
    )
    session.add(
        Transaction(
            user_id=user_id,
            amount=Decimal("50000"),
            transaction_date=datetime.now(tz=UTC).date(),
            receipt_upload_id=receipt.id,
            category_id=category.id,
        ),
    )
    session.commit()
    return storage_key


def test_find_due_only_returns_overdue_uncancelled(
    db_session: Session,
) -> None:
    now = datetime.now(tz=UTC)
    overdue = _seed_user(db_session, "overdue@example.com", scheduled_at=now - timedelta(days=1))
    _seed_user(db_session, "future@example.com", scheduled_at=now + timedelta(days=5))
    _seed_user(
        db_session,
        "cancelled@example.com",
        scheduled_at=now - timedelta(days=1),
        cancelled_at=now,
    )
    _seed_user(db_session, "active@example.com")  # no deletion request

    due = find_due_user_ids(db_session, now=now)
    assert due == [overdue.id]


def test_purge_removes_user_data_and_files(
    db_session: Session,
    storage: LocalStorageService,
) -> None:
    now = datetime.now(tz=UTC)
    # System category phải tồn tại sau purge.
    system_cat = Category(user_id=None, name="Ăn uống", is_system=True)
    db_session.add(system_cat)
    db_session.commit()

    target = _seed_user(db_session, "gone@example.com", scheduled_at=now - timedelta(days=1))
    other = _seed_user(db_session, "stay@example.com")
    assert target.id is not None
    assert other.id is not None
    target_id = target.id
    other_id = other.id

    target_key = _seed_user_data(db_session, storage, target_id)
    other_key = _seed_user_data(db_session, storage, other_id)

    result = run_purge_due_accounts(db_session, storage, now=now)

    assert result.purged_user_ids == [target_id]
    assert result.storage_errors == 0

    # Target user + data hoàn toàn biến mất.
    assert db_session.get(User, target_id) is None
    assert db_session.exec(
        select(Transaction).where(Transaction.user_id == target_id),
    ).all() == []
    assert db_session.exec(
        select(ReceiptUpload).where(ReceiptUpload.user_id == target_id),
    ).all() == []
    assert db_session.exec(
        select(Budget).where(Budget.user_id == target_id),
    ).all() == []
    assert not (Path(storage.root_dir) / target_key).exists()

    # Other user còn nguyên.
    assert db_session.get(User, other_id) is not None
    assert len(db_session.exec(
        select(Transaction).where(Transaction.user_id == other_id),
    ).all()) == 1
    assert (Path(storage.root_dir) / other_key).exists()

    # System category còn nguyên.
    assert db_session.exec(
        select(Category).where(Category.is_system.is_(True)),  # type: ignore[attr-defined]
    ).first() is not None


def test_purge_is_idempotent(
    db_session: Session,
    storage: LocalStorageService,
) -> None:
    now = datetime.now(tz=UTC)
    target = _seed_user(db_session, "gone@example.com", scheduled_at=now - timedelta(days=1))
    assert target.id is not None
    target_id = target.id
    _seed_user_data(db_session, storage, target_id)

    first = run_purge_due_accounts(db_session, storage, now=now)
    assert first.purged_user_ids == [target_id]

    # Lần 2: không còn user nào tới hạn.
    second = run_purge_due_accounts(db_session, storage, now=now)
    assert second.purged_user_ids == []
