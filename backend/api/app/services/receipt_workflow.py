from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from pfa_shared.enums import ReceiptStatus
from sqlmodel import Session, col, func, select

from app.models.entities import (
    Category,
    Invoice,
    InvoiceLineItem,
    OcrResult,
    ReceiptLineItem,
    ReceiptUpload,
    Transaction,
)
from app.schemas.receipts import (
    DraftReviewResponse,
    InvoiceLineItemResponse,
    InvoiceResponse,
    LineItemResponse,
    LinkedTransactionResponse,
    ReceiptConfirmRequest,
    ReceiptConfirmResponse,
    ReceiptImageResponse,
    ReceiptListItemResponse,
    ReceiptListMeta,
    ReceiptListResponse,
)
from app.schemas.transactions import TransactionResponse
from app.services.category_suggestion import remember_user_merchant_category
from app.services.chat.embedding_client import get_embedding_client
from app.services.draft_review import build_draft_review
from app.services.merchants import get_or_create_user_merchant_alias


@dataclass(frozen=True)
class ReceiptListFilters:
    receipt_date: date | None = None
    created_date: date | None = None
    merchant: str | None = None
    status_filter: str | None = None
    ocr_status: str | None = None
    has_transaction: bool | None = None
    has_invoice: bool | None = None
    page: int = 1
    size: int = 20


def ensure_receipt_owner(session: Session, receipt_id: int, user_id: int) -> ReceiptUpload:
    receipt = session.get(ReceiptUpload, receipt_id)
    if receipt is None or receipt.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    return receipt


def ensure_category_accessible(session: Session, category_id: int, user_id: int) -> Category:
    category = session.get(Category, category_id)
    if category is None or (not category.is_system and category.user_id != user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


def find_transaction_for_receipt(
    session: Session,
    receipt_id: int,
    user_id: int,
) -> Transaction | None:
    return session.exec(
        select(Transaction).where(
            Transaction.receipt_upload_id == receipt_id,
            Transaction.user_id == user_id,
        ),
    ).first()


def linked_transaction_response(
    transaction: Transaction | None,
) -> LinkedTransactionResponse | None:
    if transaction is None or transaction.id is None:
        return None
    return LinkedTransactionResponse(transaction_id=transaction.id, status=transaction.status)


def receipt_list_item_response(
    receipt: ReceiptUpload,
    transaction: Transaction | None,
) -> ReceiptListItemResponse:
    if receipt.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Receipt id missing",
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
        linked_transaction=linked_transaction_response(transaction),
    )


def transaction_response(
    transaction: Transaction,
    *,
    category_name: str | None = None,
    has_invoice: bool = False,
) -> TransactionResponse:
    if transaction.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transaction id missing",
        )
    return TransactionResponse(
        id=transaction.id,
        user_id=transaction.user_id,
        category_id=transaction.category_id,
        category_name=category_name,
        receipt_upload_id=transaction.receipt_upload_id,
        has_invoice=has_invoice,
        merchant_name=transaction.merchant_name,
        amount=transaction.amount,
        currency=transaction.currency,
        transaction_date=transaction.transaction_date,
        source=transaction.source,
        status=transaction.status,
        confirmed_at=transaction.confirmed_at,
        note=transaction.note,
        created_at=transaction.created_at,
    )


def list_receipts_for_user(
    session: Session,
    *,
    user_id: int,
    filters: ReceiptListFilters,
) -> ReceiptListResponse:
    statement = select(ReceiptUpload).where(ReceiptUpload.user_id == user_id)
    if filters.receipt_date is not None:
        statement = statement.where(ReceiptUpload.receipt_date == filters.receipt_date)
    if filters.created_date is not None:
        statement = statement.where(func.date(ReceiptUpload.created_at) == filters.created_date)
    if filters.merchant:
        statement = statement.where(
            col(ReceiptUpload.merchant_name).ilike(f"%{filters.merchant.strip()}%"),
        )
    if filters.status_filter:
        statement = statement.where(ReceiptUpload.status == filters.status_filter)
    if filters.ocr_status:
        statement = statement.where(ReceiptUpload.ocr_status == filters.ocr_status)
    if filters.has_invoice is not None:
        statement = statement.where(ReceiptUpload.has_invoice == filters.has_invoice)

    receipts = list(
        session.exec(
            statement.order_by(col(ReceiptUpload.created_at).desc(), col(ReceiptUpload.id).desc()),
        ).all(),
    )
    receipt_ids = [r.id for r in receipts if r.id is not None]
    tx_by_receipt: dict[int, Transaction] = {}
    if receipt_ids:
        tx_rows = session.exec(
            select(Transaction).where(
                Transaction.user_id == user_id,
                col(Transaction.receipt_upload_id).in_(receipt_ids),
            ),
        ).all()
        tx_by_receipt = {
            tx.receipt_upload_id: tx
            for tx in tx_rows
            if tx.receipt_upload_id is not None
        }

    if filters.has_transaction is not None:
        receipts = [
            receipt
            for receipt in receipts
            if ((receipt.id in tx_by_receipt) if receipt.id is not None else False)
            == filters.has_transaction
        ]

    total = len(receipts)
    start = (filters.page - 1) * filters.size
    page_rows = receipts[start:start + filters.size]
    return ReceiptListResponse(
        items=[receipt_list_item_response(r, tx_by_receipt.get(r.id or -1)) for r in page_rows],
        meta=ReceiptListMeta(total=total, page=filters.page, size=filters.size),
    )


def _receipt_line_item_response(item: ReceiptLineItem) -> LineItemResponse:
    return LineItemResponse(
        id=item.id or 0,
        line_number=item.line_number,
        item_name=item.item_name,
        quantity=item.quantity,
        unit_price=item.unit_price,
        total_price=item.total_price,
        category_id=item.category_id,
    )


def build_receipt_draft_response(
    session: Session,
    *,
    receipt_id: int,
    user_id: int,
) -> DraftReviewResponse:
    receipt = ensure_receipt_owner(session, receipt_id, user_id)
    ocr_result = session.exec(
        select(OcrResult).where(OcrResult.receipt_upload_id == receipt_id),
    ).first()
    if ocr_result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OCR result not ready")

    draft = build_draft_review(
        session=session,
        receipt=receipt,
        ocr_result=ocr_result,
        user_id=user_id,
    )
    invoice = session.exec(select(Invoice).where(Invoice.receipt_upload_id == receipt_id)).first()

    merchant_name = draft.merchant_name
    amount = draft.amount
    transaction_date = draft.transaction_date
    currency = draft.currency
    if invoice is not None:
        merchant_name = invoice.seller_name or merchant_name
        amount = invoice.grand_total or amount
        transaction_date = invoice.issue_date or transaction_date
        currency = invoice.currency or currency

    line_items = session.exec(
        select(ReceiptLineItem)
        .where(ReceiptLineItem.receipt_upload_id == receipt_id)
        .order_by(ReceiptLineItem.line_number),
    ).all()

    return DraftReviewResponse(
        receipt_id=draft.receipt_id,
        linked_transaction=linked_transaction_response(
            find_transaction_for_receipt(session, receipt_id, user_id),
        ),
        receipt_status=draft.receipt_status,
        provider=draft.provider,
        confidence=draft.confidence,
        merchant_name=merchant_name,
        transaction_date=transaction_date,
        amount=amount,
        currency=currency,
        suggested_category_id=draft.suggested_category_id,
        raw_text=draft.raw_text,
        line_items=[_receipt_line_item_response(item) for item in line_items],
    )


def update_receipt_draft_metadata(
    session: Session,
    *,
    receipt_id: int,
    user_id: int,
    payload: ReceiptConfirmRequest,
) -> DraftReviewResponse:
    receipt = ensure_receipt_owner(session, receipt_id, user_id)
    if payload.merchant_name is not None:
        receipt.merchant_name = payload.merchant_name.strip() or None
    if payload.transaction_date is not None:
        receipt.receipt_date = payload.transaction_date
    if payload.amount is not None:
        receipt.total_amount = payload.amount
    if payload.currency is not None:
        receipt.currency = payload.currency.strip().upper()
    session.add(receipt)
    session.commit()
    return build_receipt_draft_response(session, receipt_id=receipt_id, user_id=user_id)


def _build_search_text(merchant_name: str | None, note: str | None) -> str:
    return " ".join(p.strip() for p in (merchant_name, note) if p and p.strip())


def confirm_receipt_as_transaction(
    session: Session,
    *,
    receipt_id: int,
    user_id: int,
    payload: ReceiptConfirmRequest,
    skip_embedding: bool,
) -> ReceiptConfirmResponse:
    receipt = ensure_receipt_owner(session, receipt_id, user_id)
    ocr_result = session.exec(
        select(OcrResult).where(OcrResult.receipt_upload_id == receipt_id),
    ).first()
    if ocr_result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OCR result not ready")

    draft = build_draft_review(
        session=session,
        receipt=receipt,
        ocr_result=ocr_result,
        user_id=user_id,
    )
    invoice = session.exec(select(Invoice).where(Invoice.receipt_upload_id == receipt_id)).first()

    merchant_name = payload.merchant_name or receipt.merchant_name or draft.merchant_name
    transaction_date = payload.transaction_date or receipt.receipt_date or draft.transaction_date
    amount = payload.amount or receipt.total_amount or draft.amount
    currency = (payload.currency or receipt.currency or draft.currency or "VND").strip().upper()
    category_id = payload.category_id or draft.suggested_category_id
    source = "invoice" if invoice is not None else "ocr"

    if invoice is not None:
        merchant_name = payload.merchant_name or invoice.seller_name or merchant_name
        transaction_date = payload.transaction_date or invoice.issue_date or transaction_date
        amount = payload.amount or invoice.grand_total or amount
        currency = (payload.currency or invoice.currency or currency).strip().upper()

    if transaction_date is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="transaction_date is required",
        )
    if amount is None or amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="amount is required")
    if category_id is not None:
        ensure_category_accessible(session, category_id, user_id)

    alias = None
    if merchant_name:
        alias = get_or_create_user_merchant_alias(
            session,
            user_id=user_id,
            raw_name=merchant_name,
            category_id=category_id,
            source=source,
            confidence=ocr_result.confidence,
        )

    now = datetime.now(tz=UTC)
    transaction = find_transaction_for_receipt(session, receipt_id, user_id)
    if transaction is None:
        transaction = Transaction(
            user_id=user_id,
            receipt_upload_id=receipt_id,
            merchant_id=alias.merchant_id if alias else None,
            raw_merchant_name=merchant_name,
            merchant_name=merchant_name,
            category_id=category_id,
            amount=amount,
            currency=currency,
            transaction_date=transaction_date,
            note=payload.note,
            source=source,
            status="confirmed",
            confirmed_at=now,
        )
    else:
        transaction.merchant_id = alias.merchant_id if alias else None
        transaction.raw_merchant_name = merchant_name
        transaction.merchant_name = merchant_name
        transaction.category_id = category_id
        transaction.amount = amount
        transaction.currency = currency
        transaction.transaction_date = transaction_date
        transaction.note = payload.note
        transaction.source = source
        transaction.status = "confirmed"
        transaction.confirmed_at = now

    search_text = _build_search_text(merchant_name, payload.note)
    if search_text and not skip_embedding:
        try:
            transaction.search_embedding = get_embedding_client().embed_sync(search_text)
        except Exception:  # noqa: BLE001
            pass

    session.add(transaction)
    session.flush()

    if invoice is not None:
        invoice.transaction_id = transaction.id
        session.add(invoice)
    line_items = session.exec(
        select(ReceiptLineItem).where(ReceiptLineItem.receipt_upload_id == receipt_id),
    )
    for item in line_items:
        item.transaction_id = transaction.id
        if item.user_id is None:
            item.user_id = user_id
        session.add(item)

    receipt.status = ReceiptStatus.READY.value
    receipt.merchant_name = merchant_name
    receipt.receipt_date = transaction_date
    receipt.total_amount = amount
    receipt.currency = currency
    session.add(receipt)
    session.commit()
    session.refresh(transaction)

    if payload.save_merchant_alias and merchant_name and category_id is not None:
        remember_user_merchant_category(
            session=session,
            user_id=user_id,
            merchant_name=merchant_name,
            category_id=category_id,
        )

    if transaction.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transaction id missing",
        )
    return ReceiptConfirmResponse(
        receipt_id=receipt_id,
        receipt_status=receipt.status,
        transaction_id=transaction.id,
    )


def receipt_image_response(
    session: Session,
    *,
    receipt_id: int,
    user_id: int,
) -> ReceiptImageResponse:
    receipt = ensure_receipt_owner(session, receipt_id, user_id)
    return ReceiptImageResponse(
        receipt_id=receipt.id or receipt_id,
        file_name=receipt.file_name,
        content_type=receipt.content_type,
        storage_key=receipt.storage_key,
    )


def reset_receipt_for_retry(
    session: Session,
    *,
    receipt_id: int,
    user_id: int,
) -> ReceiptUpload:
    receipt = ensure_receipt_owner(session, receipt_id, user_id)
    transaction = find_transaction_for_receipt(session, receipt_id, user_id)
    if transaction is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Confirmed receipt cannot be retried",
        )

    receipt.status = ReceiptStatus.PROCESSING.value
    receipt.ocr_status = "pending"
    receipt.error_code = None
    receipt.error_message = None
    session.add(receipt)
    session.commit()
    session.refresh(receipt)
    return receipt


def delete_receipt_for_user(
    session: Session,
    *,
    receipt_id: int,
    user_id: int,
) -> ReceiptUpload:
    receipt = ensure_receipt_owner(session, receipt_id, user_id)
    transaction = find_transaction_for_receipt(session, receipt_id, user_id)
    if transaction is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Receipt is linked to a confirmed transaction",
        )

    ocr_result = session.exec(
        select(OcrResult).where(OcrResult.receipt_upload_id == receipt_id),
    ).first()
    if ocr_result is not None:
        session.delete(ocr_result)

    line_items = session.exec(
        select(ReceiptLineItem).where(ReceiptLineItem.receipt_upload_id == receipt_id),
    ).all()
    for item in line_items:
        session.delete(item)

    invoice = session.exec(
        select(Invoice).where(Invoice.receipt_upload_id == receipt_id),
    ).first()
    if invoice is not None:
        invoice_line_items = session.exec(
            select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice.id),
        ).all()
        for item in invoice_line_items:
            session.delete(item)
        session.delete(invoice)

    session.delete(receipt)
    session.commit()
    return receipt


def receipt_line_items_response(
    session: Session,
    *,
    receipt_id: int,
    user_id: int,
) -> list[LineItemResponse]:
    ensure_receipt_owner(session, receipt_id, user_id)
    rows = session.exec(
        select(ReceiptLineItem)
        .where(ReceiptLineItem.receipt_upload_id == receipt_id)
        .order_by(ReceiptLineItem.line_number),
    ).all()
    return [_receipt_line_item_response(item) for item in rows]


def receipt_transaction_response(
    session: Session,
    *,
    receipt_id: int,
    user_id: int,
) -> TransactionResponse:
    ensure_receipt_owner(session, receipt_id, user_id)
    transaction = find_transaction_for_receipt(session, receipt_id, user_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    category_name = None
    if transaction.category_id is not None:
        category = session.get(Category, transaction.category_id)
        category_name = category.name if category else None
    return transaction_response(transaction, category_name=category_name)


def invoice_response_for_receipt(
    session: Session,
    *,
    receipt_id: int,
    user_id: int,
) -> InvoiceResponse:
    ensure_receipt_owner(session, receipt_id, user_id)
    invoice = session.exec(
        select(Invoice).where(Invoice.receipt_upload_id == receipt_id),
    ).first()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    line_items = session.exec(
        select(InvoiceLineItem)
        .where(InvoiceLineItem.invoice_id == invoice.id)
        .order_by(InvoiceLineItem.line_number),
    ).all()

    return InvoiceResponse(
        id=invoice.id or 0,
        receipt_upload_id=invoice.receipt_upload_id,
        invoice_number=invoice.invoice_number,
        template_symbol=invoice.template_symbol,
        issue_date=invoice.issue_date,
        tax_lookup_code=invoice.tax_lookup_code,
        currency=invoice.currency,
        seller_name=invoice.seller_name,
        seller_tax_id=invoice.seller_tax_id,
        seller_address=invoice.seller_address,
        buyer_name=invoice.buyer_name,
        buyer_tax_id=invoice.buyer_tax_id,
        buyer_address=invoice.buyer_address,
        payment_method=invoice.payment_method,
        subtotal_before_tax=invoice.subtotal_before_tax,
        total_tax=invoice.total_tax,
        grand_total=invoice.grand_total,
        amount_in_words=invoice.amount_in_words,
        digital_signature=invoice.digital_signature,
        signing_date=invoice.signing_date,
        lookup_link=invoice.lookup_link,
        line_items=[
            InvoiceLineItemResponse(
                id=item.id or 0,
                line_number=item.line_number,
                item_name=item.item_name,
                unit=item.unit,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
                vat_rate=item.vat_rate,
                vat_amount=item.vat_amount,
            )
            for item in line_items
        ],
    )
