"""Billing read APIs for Settings UI."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, func, select

from app.core.config import get_settings
from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import Insight, Invoice, ReceiptUpload, Transaction, User
from app.schemas.billing import (
    BillingCheckoutSessionResponse,
    BillingHistoryResponse,
    BillingPlanResponse,
    BillingUsageResponse,
)

router = APIRouter(prefix="/billing", tags=["billing"])


def _require_user_id(current_user: User) -> int:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return current_user.id


@router.get("/plan", response_model=BillingPlanResponse)
def get_billing_plan(current_user: User = Depends(get_current_user)) -> BillingPlanResponse:
    _require_user_id(current_user)
    return BillingPlanResponse(
        plan_id="local_dev",
        name="Local Development",
        status="active",
        currency=current_user.currency,
        monthly_price="0.00",
        features=["transactions", "receipt_ocr", "analytics", "assistant"],
    )


@router.get("/usage", response_model=BillingUsageResponse)
def get_billing_usage(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BillingUsageResponse:
    user_id = _require_user_id(current_user)
    transaction_count = session.exec(
        select(func.count(Transaction.id)).where(Transaction.user_id == user_id),
    ).one()
    receipt_count = session.exec(
        select(func.count(ReceiptUpload.id)).where(ReceiptUpload.user_id == user_id),
    ).one()
    invoice_count = session.exec(
        select(func.count(Invoice.id)).where(Invoice.user_id == user_id),
    ).one()
    insight_count = session.exec(
        select(func.count(Insight.id)).where(Insight.user_id == user_id),
    ).one()
    return BillingUsageResponse(
        transaction_count=int(transaction_count or 0),
        receipt_count=int(receipt_count or 0),
        invoice_count=int(invoice_count or 0),
        insight_count=int(insight_count or 0),
        storage_backend=get_settings().storage_backend,
    )


@router.get("/history", response_model=BillingHistoryResponse)
def get_billing_history(current_user: User = Depends(get_current_user)) -> BillingHistoryResponse:
    _require_user_id(current_user)
    return BillingHistoryResponse(items=[])


@router.post("/checkout-session", response_model=BillingCheckoutSessionResponse)
def create_checkout_session(
    current_user: User = Depends(get_current_user),
) -> BillingCheckoutSessionResponse:
    _require_user_id(current_user)
    return BillingCheckoutSessionResponse(
        status="not_configured",
        checkout_url=None,
        message="Billing checkout provider is not configured in this environment.",
    )


__all__ = ["router"]
