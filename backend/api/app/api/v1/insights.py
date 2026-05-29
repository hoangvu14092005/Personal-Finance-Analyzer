"""Row-level Insights APIs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import User
from app.schemas.insights import (
    InsightFeedbackCreate,
    InsightFeedbackResponse,
    InsightGenerateRequest,
    InsightGenerateResponse,
    InsightListResponse,
    InsightResponse,
    InsightUpdate,
)
from app.services.date_ranges import InvalidDateRangeError
from app.services.insights import (
    InsightNotFoundError,
    create_insight_feedback,
    ensure_insight_owner,
    generate_rule_based_insights,
    insight_to_payload,
    list_insights_for_user,
    resolve_insight_range,
    update_insight_status,
)

router = APIRouter(prefix="/insights", tags=["insights"])


def _require_user_id(current_user: User) -> int:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return current_user.id


def _insight_response(payload: dict[str, object]) -> InsightResponse:
    return InsightResponse(**payload)


@router.get("", response_model=InsightListResponse)
def list_insights(
    status_filter: str | None = Query(default=None, alias="status"),
    type_filter: str | None = Query(default=None, alias="type"),
    severity: str | None = Query(default=None),
    limit: int = Query(20, ge=1, le=100),
    before_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> InsightListResponse:
    user_id = _require_user_id(current_user)
    rows, has_more, next_before = list_insights_for_user(
        session,
        user_id=user_id,
        status=status_filter,
        type_filter=type_filter,
        severity=severity,
        limit=limit,
        before_id=before_id,
    )
    return InsightListResponse(
        items=[_insight_response(insight_to_payload(row)) for row in rows],
        has_more=has_more,
        next_before_id=next_before,
    )


@router.post("/generate", response_model=InsightGenerateResponse)
def generate_insights(
    payload: InsightGenerateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> InsightGenerateResponse:
    user_id = _require_user_id(current_user)
    try:
        preset, range_ = resolve_insight_range(
            payload.range,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
    except (ValueError, InvalidDateRangeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    insights = generate_rule_based_insights(
        session,
        user_id=user_id,
        range_=range_,
        preset=preset,
        force_refresh=payload.force_refresh,
        types=payload.types,
    )
    return InsightGenerateResponse(
        items=[_insight_response(insight_to_payload(row)) for row in insights],
        generated_count=len(insights),
    )


@router.get("/{insight_id}", response_model=InsightResponse)
def get_insight(
    insight_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> InsightResponse:
    user_id = _require_user_id(current_user)
    try:
        insight = ensure_insight_owner(session, insight_id=insight_id, user_id=user_id)
    except InsightNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        ) from exc
    return _insight_response(insight_to_payload(insight))


@router.patch("/{insight_id}", response_model=InsightResponse)
def patch_insight(
    insight_id: int,
    payload: InsightUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> InsightResponse:
    user_id = _require_user_id(current_user)
    try:
        insight = update_insight_status(
            session,
            insight_id=insight_id,
            user_id=user_id,
            status=payload.status,
        )
    except InsightNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        ) from exc
    return _insight_response(insight_to_payload(insight))


@router.post("/{insight_id}/feedback", response_model=InsightFeedbackResponse)
def post_insight_feedback(
    insight_id: int,
    payload: InsightFeedbackCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> InsightFeedbackResponse:
    user_id = _require_user_id(current_user)
    try:
        feedback = create_insight_feedback(
            session,
            insight_id=insight_id,
            user_id=user_id,
            rating=payload.rating,
            comment=payload.comment,
        )
    except InsightNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        ) from exc
    if feedback.id is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Missing id")
    return InsightFeedbackResponse(
        id=feedback.id,
        insight_id=feedback.insight_id,
        rating=feedback.rating,  # type: ignore[arg-type]
        comment=feedback.comment,
        created_at=feedback.created_at,
    )


__all__ = ["router"]
