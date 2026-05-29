"""Direct invoice retrieval APIs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import User
from app.schemas.receipts import InvoiceLineItemResponse, InvoiceResponse
from app.services.invoices import invoice_detail_response, list_invoice_line_items

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _require_user_id(current_user: User) -> int:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return current_user.id


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> InvoiceResponse:
    user_id = _require_user_id(current_user)
    return invoice_detail_response(session, invoice_id=invoice_id, user_id=user_id)


@router.get("/{invoice_id}/line-items", response_model=list[InvoiceLineItemResponse])
def get_invoice_line_items(
    invoice_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[InvoiceLineItemResponse]:
    user_id = _require_user_id(current_user)
    return list_invoice_line_items(session, invoice_id=invoice_id, user_id=user_id)


__all__ = ["router"]
