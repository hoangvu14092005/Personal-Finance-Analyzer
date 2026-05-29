"""Merchant search APIs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import User
from app.schemas.merchants import MerchantSearchResponse
from app.services.merchants import search_merchants_for_user

router = APIRouter(prefix="/merchants", tags=["merchants"])


def _require_user_id(current_user: User) -> int:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return current_user.id


@router.get("/search", response_model=MerchantSearchResponse)
def search_merchants(
    q: str = Query(..., min_length=1, max_length=255),
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> MerchantSearchResponse:
    user_id = _require_user_id(current_user)
    return MerchantSearchResponse(
        items=search_merchants_for_user(session, user_id=user_id, query=q, limit=limit),
    )


__all__ = ["router"]
