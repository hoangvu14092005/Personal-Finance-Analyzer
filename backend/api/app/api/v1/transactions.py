"""Transaction APIs (Phase 3.1 / 3.5 / 3.7 / 3.8 / 3.9).

Endpoints:
- POST   /api/v1/transactions          : tao transaction (manual entry hoac tu OCR draft)
- GET    /api/v1/transactions          : list transaction co filter + pagination
- PUT    /api/v1/transactions/{id}     : update transaction (partial fields)
- DELETE /api/v1/transactions/{id}     : xoa transaction (hard delete)
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session, col, func, select

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import Category, Invoice, InvoiceLineItem, ReceiptUpload, Transaction, User
from app.schemas.receipts import InvoiceLineItemResponse, InvoiceResponse
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


def _build_search_text(merchant_name: str | None, note: str | None) -> str:
    """Build text để embed cho semantic_search_transactions."""
    parts = [p.strip() for p in (merchant_name, note) if p and p.strip()]
    return " ".join(parts)

router = APIRouter(prefix="/transactions", tags=["transactions"])

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _to_response(
    transaction: Transaction,
    *,
    has_invoice: bool = False,
    category_name: str | None = None,
) -> TransactionResponse:
    if transaction.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transaction id missing after persist",
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
        note=transaction.note,
        created_at=transaction.created_at,
    )


def _ensure_receipt_owner(
    session: Session,
    receipt_id: int,
    user_id: int,
) -> ReceiptUpload:
    receipt = session.get(ReceiptUpload, receipt_id)
    if receipt is None or receipt.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found",
        )
    return receipt


def _ensure_transaction_owner(
    session: Session,
    transaction_id: int,
    user_id: int,
) -> Transaction:
    transaction = session.get(Transaction, transaction_id)
    if transaction is None or transaction.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    return transaction


def _ensure_category_accessible(
    session: Session,
    category_id: int,
    user_id: int,
) -> Category:
    category = session.get(Category, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    is_owned = category.user_id == user_id
    if not category.is_system and not is_owned:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    return category


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    payload: TransactionCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )

    if payload.receipt_upload_id is not None:
        _ensure_receipt_owner(session, payload.receipt_upload_id, current_user.id)

    resolved_category_id = payload.category_id
    if resolved_category_id is not None:
        _ensure_category_accessible(session, resolved_category_id, current_user.id)
    else:
        resolved_category_id = suggest_category_for_merchant(
            session,
            current_user.id,
            payload.merchant_name,
        )

    transaction = Transaction(
        user_id=current_user.id,
        category_id=resolved_category_id,
        receipt_upload_id=payload.receipt_upload_id,
        merchant_name=payload.merchant_name,
        amount=payload.amount,
        currency=payload.currency,
        transaction_date=payload.transaction_date,
        note=payload.note,
    )

    # Phase 7 RAG: embed "merchant + note" for semantic_search_transactions.
    # Fail-soft: nếu embedding fail (model không load được), vẫn tạo transaction.
    search_text = _build_search_text(payload.merchant_name, payload.note)
    import os
    if search_text and os.getenv("PFA_SKIP_EMBEDDING") != "1":
        try:
            embedding_client = get_embedding_client()
            transaction.search_embedding = embedding_client.embed_sync(search_text)
        except Exception:  # noqa: BLE001
            # Log và tiếp tục — search_embedding nullable, có thể backfill sau.
            pass

    session.add(transaction)
    session.commit()
    session.refresh(transaction)

    if (
        payload.merchant_name
        and payload.category_id is not None
    ):
        remember_user_merchant_category(
            session=session,
            user_id=current_user.id,
            merchant_name=payload.merchant_name,
            category_id=payload.category_id,
        )

    return _to_response(transaction)


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    category_id: int | None = Query(default=None, gt=0),
    merchant: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> TransactionListResponse:
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )

    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be on or before end_date",
        )

    base_query = select(Transaction).where(Transaction.user_id == current_user.id)
    if start_date is not None:
        base_query = base_query.where(Transaction.transaction_date >= start_date)
    if end_date is not None:
        base_query = base_query.where(Transaction.transaction_date <= end_date)
    if category_id is not None:
        base_query = base_query.where(Transaction.category_id == category_id)
    if merchant:
        like_pattern = f"%{merchant.strip()}%"
        base_query = base_query.where(col(Transaction.merchant_name).ilike(like_pattern))

    count_query = select(func.count()).select_from(base_query.subquery())
    total = session.exec(count_query).one()

    paged_query = (
        base_query.order_by(
            col(Transaction.transaction_date).desc(),
            col(Transaction.id).desc(),
        )
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = session.exec(paged_query).all()

    # Enrich with category_name and has_invoice
    enriched_items: list[TransactionResponse] = []
    for tx in rows:
        # Resolve category name
        cat_name: str | None = None
        if tx.category_id is not None:
            cat = session.get(Category, tx.category_id)
            if cat is not None:
                cat_name = cat.name

        # Check if invoice exists for this transaction's receipt
        has_inv = False
        if tx.receipt_upload_id is not None:
            inv = session.exec(
                select(Invoice).where(Invoice.receipt_upload_id == tx.receipt_upload_id),
            ).first()
            has_inv = inv is not None

        enriched_items.append(
            _to_response(tx, has_invoice=has_inv, category_name=cat_name)
        )

    return TransactionListResponse(
        items=enriched_items,
        meta=TransactionListMeta(total=int(total), page=page, size=size),
    )


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    """Update transaction (Phase 3.7).

    Sửa partial: chỉ field nào được set trong body mới ghi đè. Validate ownership
    của cả transaction và category mới (nếu đổi). Khi đổi cả `merchant_name` +
    `category_id` sang giá trị non-null, lưu mapping vào `UserMerchantMapping`
    để các draft sau gợi ý đúng category.
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )

    transaction = _ensure_transaction_owner(session, transaction_id, current_user.id)

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        # Body rỗng -> không có gì để update; trả về state hiện tại để client biết
        # request đã được xử lý nhưng không thay đổi.
        return _to_response(transaction)

    if "category_id" in update_data and update_data["category_id"] is not None:
        _ensure_category_accessible(
            session,
            update_data["category_id"],
            current_user.id,
        )

    for field, value in update_data.items():
        setattr(transaction, field, value)

    # Re-embed search_embedding khi merchant_name hoặc note đổi (Phase 7 RAG).
    import os
    skip_embedding = os.getenv("PFA_SKIP_EMBEDDING") == "1"
    should_reembed = (
        "merchant_name" in update_data or "note" in update_data
    ) and not skip_embedding
    if should_reembed:
        search_text = _build_search_text(transaction.merchant_name, transaction.note)
        if search_text:
            try:
                embedding_client = get_embedding_client()
                transaction.search_embedding = embedding_client.embed_sync(search_text)
            except Exception:  # noqa: BLE001
                pass
        else:
            transaction.search_embedding = None

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
            user_id=current_user.id,
            merchant_name=transaction.merchant_name,
            category_id=transaction.category_id,
        )

    return _to_response(transaction)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Hard-delete transaction (Phase 3.8).

    Hard delete vì MVP chưa có audit trail / soft-delete; row xóa vĩnh viễn.
    Dashboard summary tự cập nhật vì chỉ aggregate từ rows hiện tại.
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )

    transaction = _ensure_transaction_owner(session, transaction_id, current_user.id)
    session.delete(transaction)
    session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{transaction_id}/invoice", response_model=InvoiceResponse)
def get_transaction_invoice(
    transaction_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> InvoiceResponse:
    """Return full invoice data for a transaction's associated receipt."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )

    transaction = _ensure_transaction_owner(session, transaction_id, current_user.id)

    if transaction.receipt_upload_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    invoice = session.exec(
        select(Invoice).where(Invoice.receipt_upload_id == transaction.receipt_upload_id),
    ).first()
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

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
