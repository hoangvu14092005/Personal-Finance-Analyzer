from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlmodel import Session, col, func, select

from app.models.entities import Category, Invoice, ReceiptLineItem, ReceiptUpload, Transaction
from app.schemas.receipts import InvoiceResponse, LinkedTransactionResponse, ReceiptListItemResponse
from app.schemas.transactions import (
    TransactionCreate,
    TransactionListMeta,
    TransactionListResponse,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.category_suggestion import (
    remember_user_merchant_category,
    suggest_category_for_merchant,
)
from app.services.chat.embedding_client import get_embedding_client
from app.services.merchants import get_or_create_user_merchant_alias
from app.services.receipt_workflow import invoice_response_for_receipt, transaction_response


@dataclass(frozen=True)
class TransactionListFilters:
    start_date: date | None = None
    end_date: date | None = None
    category_id: int | None = None
    merchant: str | None = None
    page: int = 1
    size: int = 20


def ensure_receipt_owner(session: Session, receipt_id: int, user_id: int) -> ReceiptUpload:
    receipt = session.get(ReceiptUpload, receipt_id)
    if receipt is None or receipt.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    return receipt


def ensure_transaction_owner(
    session: Session,
    transaction_id: int,
    user_id: int,
) -> Transaction:
    transaction = session.get(Transaction, transaction_id)
    if transaction is None or transaction.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction


def ensure_category_accessible(session: Session, category_id: int, user_id: int) -> Category:
    category = session.get(Category, category_id)
    if category is None or (not category.is_system and category.user_id != user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


def _build_search_text(merchant_name: str | None, note: str | None) -> str:
    parts = [p.strip() for p in (merchant_name, note) if p and p.strip()]
    return " ".join(parts)


def _embed_transaction_search_text(
    transaction: Transaction,
    *,
    merchant_name: str | None,
    note: str | None,
    skip_embedding: bool,
) -> None:
    search_text = _build_search_text(merchant_name, note)
    if not search_text:
        transaction.search_embedding = None
        return
    if skip_embedding:
        return
    try:
        transaction.search_embedding = get_embedding_client().embed_sync(search_text)
    except Exception:  # noqa: BLE001
        pass


def create_transaction_for_user(
    session: Session,
    *,
    user_id: int,
    payload: TransactionCreate,
    skip_embedding: bool,
) -> TransactionResponse:
    if payload.receipt_upload_id is not None:
        ensure_receipt_owner(session, payload.receipt_upload_id, user_id)
        existing_for_receipt = session.exec(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.receipt_upload_id == payload.receipt_upload_id,
            ),
        ).first()
        if existing_for_receipt is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Receipt already has a transaction",
            )

    resolved_category_id = payload.category_id
    if resolved_category_id is not None:
        ensure_category_accessible(session, resolved_category_id, user_id)
    else:
        resolved_category_id = suggest_category_for_merchant(
            session,
            user_id,
            payload.merchant_name,
        )

    source = "receipt" if payload.receipt_upload_id is not None else "manual"
    merchant_alias = None
    if payload.merchant_name:
        merchant_alias = get_or_create_user_merchant_alias(
            session,
            user_id=user_id,
            raw_name=payload.merchant_name,
            category_id=resolved_category_id,
            source=source,
            confidence=1.0 if payload.category_id is not None else None,
        )

    transaction = Transaction(
        user_id=user_id,
        merchant_id=merchant_alias.merchant_id if merchant_alias else None,
        category_id=resolved_category_id,
        receipt_upload_id=payload.receipt_upload_id,
        raw_merchant_name=payload.merchant_name,
        merchant_name=payload.merchant_name,
        amount=payload.amount,
        currency=payload.currency,
        transaction_date=payload.transaction_date,
        note=payload.note,
        source=source,
        status="confirmed",
        confirmed_at=datetime.now(tz=UTC),
    )
    _embed_transaction_search_text(
        transaction,
        merchant_name=payload.merchant_name,
        note=payload.note,
        skip_embedding=skip_embedding,
    )

    session.add(transaction)
    session.commit()
    session.refresh(transaction)

    if payload.merchant_name and payload.category_id is not None:
        remember_user_merchant_category(
            session=session,
            user_id=user_id,
            merchant_name=payload.merchant_name,
            category_id=payload.category_id,
        )

    return transaction_response(transaction)


def list_transactions_for_user(
    session: Session,
    *,
    user_id: int,
    filters: TransactionListFilters,
) -> TransactionListResponse:
    if filters.start_date is not None and filters.end_date is not None:
        if filters.start_date > filters.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be on or before end_date",
            )

    base_query = select(Transaction).where(Transaction.user_id == user_id)
    if filters.start_date is not None:
        base_query = base_query.where(Transaction.transaction_date >= filters.start_date)
    if filters.end_date is not None:
        base_query = base_query.where(Transaction.transaction_date <= filters.end_date)
    if filters.category_id is not None:
        base_query = base_query.where(Transaction.category_id == filters.category_id)
    if filters.merchant:
        like_pattern = f"%{filters.merchant.strip()}%"
        base_query = base_query.where(col(Transaction.merchant_name).ilike(like_pattern))

    count_query = select(func.count()).select_from(base_query.subquery())
    total = session.exec(count_query).one()
    rows = session.exec(
        base_query.order_by(
            col(Transaction.transaction_date).desc(),
            col(Transaction.id).desc(),
        )
        .offset((filters.page - 1) * filters.size)
        .limit(filters.size),
    ).all()

    enriched_items: list[TransactionResponse] = []
    for tx in rows:
        category_name: str | None = None
        if tx.category_id is not None:
            category = session.get(Category, tx.category_id)
            category_name = category.name if category else None

        has_invoice = False
        if tx.receipt_upload_id is not None:
            invoice = session.exec(
                select(Invoice).where(Invoice.receipt_upload_id == tx.receipt_upload_id),
            ).first()
            has_invoice = invoice is not None

        enriched_items.append(
            transaction_response(tx, has_invoice=has_invoice, category_name=category_name),
        )

    return TransactionListResponse(
        items=enriched_items,
        meta=TransactionListMeta(total=int(total), page=filters.page, size=filters.size),
    )


def get_transaction_response_for_user(
    session: Session,
    *,
    transaction_id: int,
    user_id: int,
) -> TransactionResponse:
    transaction = ensure_transaction_owner(session, transaction_id, user_id)
    category_name = None
    if transaction.category_id is not None:
        category = session.get(Category, transaction.category_id)
        category_name = category.name if category else None

    has_invoice = False
    if transaction.receipt_upload_id is not None:
        invoice = session.exec(
            select(Invoice).where(Invoice.receipt_upload_id == transaction.receipt_upload_id),
        ).first()
        has_invoice = invoice is not None

    return transaction_response(
        transaction,
        category_name=category_name,
        has_invoice=has_invoice,
    )


def update_transaction_for_user(
    session: Session,
    *,
    transaction_id: int,
    user_id: int,
    payload: TransactionUpdate,
    skip_embedding: bool,
) -> TransactionResponse:
    transaction = ensure_transaction_owner(session, transaction_id, user_id)
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return transaction_response(transaction)

    if "category_id" in update_data and update_data["category_id"] is not None:
        ensure_category_accessible(session, update_data["category_id"], user_id)

    for field, value in update_data.items():
        setattr(transaction, field, value)

    if "merchant_name" in update_data:
        transaction.raw_merchant_name = transaction.merchant_name

    if transaction.merchant_name:
        alias = get_or_create_user_merchant_alias(
            session,
            user_id=user_id,
            raw_name=transaction.merchant_name,
            category_id=transaction.category_id,
            source=transaction.source,
            confidence=1.0 if transaction.category_id is not None else None,
        )
        transaction.merchant_id = alias.merchant_id if alias else None
    elif "merchant_name" in update_data:
        transaction.merchant_id = None

    should_reembed = "merchant_name" in update_data or "note" in update_data
    if should_reembed:
        _embed_transaction_search_text(
            transaction,
            merchant_name=transaction.merchant_name,
            note=transaction.note,
            skip_embedding=skip_embedding,
        )

    session.add(transaction)
    session.commit()
    session.refresh(transaction)

    if (
        transaction.merchant_name
        and transaction.category_id is not None
        and ("merchant_name" in update_data or "category_id" in update_data)
    ):
        remember_user_merchant_category(
            session=session,
            user_id=user_id,
            merchant_name=transaction.merchant_name,
            category_id=transaction.category_id,
        )

    return transaction_response(transaction)


def delete_transaction_for_user(
    session: Session,
    *,
    transaction_id: int,
    user_id: int,
) -> None:
    transaction = ensure_transaction_owner(session, transaction_id, user_id)
    if transaction.receipt_upload_id is not None:
        invoice = session.exec(
            select(Invoice).where(Invoice.transaction_id == transaction.id),
        ).first()
        if invoice is not None:
            invoice.transaction_id = None
            session.add(invoice)

        line_items = session.exec(
            select(ReceiptLineItem).where(ReceiptLineItem.transaction_id == transaction.id),
        ).all()
        for item in line_items:
            item.transaction_id = None
            session.add(item)

    session.delete(transaction)
    session.commit()


def transaction_receipt_response(
    session: Session,
    *,
    transaction_id: int,
    user_id: int,
) -> ReceiptListItemResponse:
    transaction = ensure_transaction_owner(session, transaction_id, user_id)
    if transaction.receipt_upload_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    receipt = ensure_receipt_owner(session, transaction.receipt_upload_id, user_id)
    if receipt.id is None or transaction.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing id",
        )
    return ReceiptListItemResponse(
        receipt_id=receipt.id,
        file_name=receipt.file_name,
        content_type=receipt.content_type,
        status=receipt.status,
        ocr_status=receipt.ocr_status,
        merchant_name=receipt.merchant_name,
        receipt_date=receipt.receipt_date,
        total_amount=receipt.total_amount,
        currency=receipt.currency,
        has_invoice=receipt.has_invoice,
        created_at=receipt.created_at,
        linked_transaction=LinkedTransactionResponse(
            transaction_id=transaction.id,
            status=transaction.status,
        ),
    )


def transaction_invoice_response(
    session: Session,
    *,
    transaction_id: int,
    user_id: int,
) -> InvoiceResponse:
    transaction = ensure_transaction_owner(session, transaction_id, user_id)
    if transaction.receipt_upload_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice_response_for_receipt(
        session,
        receipt_id=transaction.receipt_upload_id,
        user_id=user_id,
    )
