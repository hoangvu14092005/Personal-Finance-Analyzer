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
from app.models.entities import Category, ReceiptUpload, Transaction, User
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

router = APIRouter(prefix="/transactions", tags=["transactions"])

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _to_response(transaction: Transaction) -> TransactionResponse:
    if transaction.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transaction id missing after persist",
        )

    return TransactionResponse(
        id=transaction.id,
        user_id=transaction.user_id,
        category_id=transaction.category_id,
        receipt_upload_id=transaction.receipt_upload_id,
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

    return TransactionListResponse(
        items=[_to_response(row) for row in rows],
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
