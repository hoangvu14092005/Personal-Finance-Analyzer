"""Transaction APIs (Phase 3.1 / 3.5 / 3.7 / 3.8 / 3.9).

Endpoints:
- POST   /api/v1/transactions          : tao transaction (manual entry hoac tu OCR draft)
- GET    /api/v1/transactions          : list transaction co filter + pagination
- GET    /api/v1/transactions/{id}     : get transaction detail
- PATCH  /api/v1/transactions/{id}     : update transaction (partial fields)
- PUT    /api/v1/transactions/{id}     : update transaction (partial fields)
- DELETE /api/v1/transactions/{id}     : xoa transaction (hard delete)
"""
from __future__ import annotations

import os
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import User
from app.schemas.receipts import InvoiceResponse, ReceiptListItemResponse
from app.schemas.transactions import (
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.audit import record_audit_event
from app.services.transaction_workflow import (
    TransactionListFilters,
    create_transaction_for_user,
    delete_transaction_for_user,
    get_transaction_response_for_user,
    list_transactions_for_user,
    transaction_invoice_response,
    transaction_receipt_response,
    update_transaction_for_user,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


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

    transaction = create_transaction_for_user(
        session,
        user_id=current_user.id,
        payload=payload,
        skip_embedding=os.getenv("PFA_SKIP_EMBEDDING") == "1",
    )
    record_audit_event(
        session,
        user_id=current_user.id,
        event="transaction.created",
        target_type="transaction",
        target_id=transaction.id,
        metadata={"source": transaction.source},
        commit=True,
    )
    return transaction


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

    return list_transactions_for_user(
        session,
        user_id=current_user.id,
        filters=TransactionListFilters(
            start_date=start_date,
            end_date=end_date,
            category_id=category_id,
            merchant=merchant,
            page=page,
            size=size,
        ),
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )

    return get_transaction_response_for_user(
        session,
        transaction_id=transaction_id,
        user_id=current_user.id,
    )


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def patch_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    return update_transaction(
        transaction_id=transaction_id,
        payload=payload,
        session=session,
        current_user=current_user,
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

    transaction = update_transaction_for_user(
        session,
        transaction_id=transaction_id,
        user_id=current_user.id,
        payload=payload,
        skip_embedding=os.getenv("PFA_SKIP_EMBEDDING") == "1",
    )
    record_audit_event(
        session,
        user_id=current_user.id,
        event="transaction.updated",
        target_type="transaction",
        target_id=transaction_id,
        metadata={"fields": ",".join(sorted(payload.model_dump(exclude_unset=True).keys()))},
        commit=True,
    )
    return transaction


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

    delete_transaction_for_user(session, transaction_id=transaction_id, user_id=current_user.id)
    record_audit_event(
        session,
        user_id=current_user.id,
        event="transaction.deleted",
        target_type="transaction",
        target_id=transaction_id,
        commit=True,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{transaction_id}/receipt", response_model=ReceiptListItemResponse)
def get_transaction_receipt(
    transaction_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReceiptListItemResponse:
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )

    return transaction_receipt_response(
        session,
        transaction_id=transaction_id,
        user_id=current_user.id,
    )


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

    return transaction_invoice_response(
        session,
        transaction_id=transaction_id,
        user_id=current_user.id,
    )
