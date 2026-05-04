"""Budget APIs (Phase 5.2 + 5.3).

Endpoints:
- POST   /api/v1/budgets                  : tạo budget mới cho (category, period_month)
- GET    /api/v1/budgets                  : list budgets của user, filter theo period_month
- PUT    /api/v1/budgets/{budget_id}      : update amount (không cho đổi category/period)
- DELETE /api/v1/budgets/{budget_id}      : xóa budget (hard delete)
- GET    /api/v1/budgets/usage            : tính usage cho 1 period_month

Business rules:
- Chỉ user sở hữu budget mới access được (ownership check).
- Category phải `is_system=True` hoặc `user_id == current_user.id`.
- (category_id, period_month) unique / user — duplicate raise 409.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import Budget, Category, User
from app.schemas.budgets import (
    BudgetCreate,
    BudgetListResponse,
    BudgetResponse,
    BudgetUpdate,
    BudgetUsageResponse,
)
from app.services.budgets import (
    BudgetAlreadyExistsError,
    BudgetNotFoundError,
    compute_budget_usage,
    create_budget,
    delete_budget,
    get_budget_for_user,
    list_budgets_for_user,
    update_budget_amount,
)

router = APIRouter(prefix="/budgets", tags=["budgets"])

# Regex period_month đã validate trong schema, router dùng lại như simple type.


def _to_response(budget: Budget) -> BudgetResponse:
    if budget.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Budget id missing after persist",
        )
    return BudgetResponse(
        id=budget.id,
        user_id=budget.user_id,
        category_id=budget.category_id,
        period_month=budget.period_month,
        amount=budget.amount,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


def _ensure_category_accessible(
    session: Session,
    category_id: int,
    user_id: int,
) -> Category:
    """Category phải là system hoặc thuộc user. Ngược lại 404 (hide khỏi user)."""
    category = session.get(Category, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    if not category.is_system and category.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return category


def _require_user_id(current_user: User) -> int:
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )
    return current_user.id


@router.post(
    "",
    response_model=BudgetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_budget_endpoint(
    payload: BudgetCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BudgetResponse:
    user_id = _require_user_id(current_user)
    _ensure_category_accessible(session, payload.category_id, user_id)

    try:
        budget = create_budget(
            session=session,
            user_id=user_id,
            category_id=payload.category_id,
            period_month=payload.period_month,
            amount=payload.amount,
        )
    except BudgetAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return _to_response(budget)


@router.get("", response_model=BudgetListResponse)
def list_budgets_endpoint(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    period_month: str | None = Query(
        default=None,
        min_length=7,
        max_length=7,
        description="Filter theo YYYY-MM (optional)",
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
    ),
) -> BudgetListResponse:
    user_id = _require_user_id(current_user)
    rows = list_budgets_for_user(session, user_id, period_month=period_month)
    return BudgetListResponse(items=[_to_response(b) for b in rows])


@router.get("/usage", response_model=list[BudgetUsageResponse])
def get_budget_usage_endpoint(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    period_month: str = Query(
        ...,
        min_length=7,
        max_length=7,
        description="YYYY-MM (required)",
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
    ),
) -> list[BudgetUsageResponse]:
    """Tính usage cho tất cả budget của user trong period_month."""
    user_id = _require_user_id(current_user)
    usages = compute_budget_usage(session, user_id, period_month)
    return [
        BudgetUsageResponse(
            budget_id=u.budget_id,
            category_id=u.category_id,
            category_name=u.category_name,
            category_color=u.category_color,
            period_month=u.period_month,
            budget_amount=u.budget_amount,
            spent_amount=u.spent_amount,
            remaining_amount=u.remaining_amount,
            percent_used=u.percent_used,
            status=u.status,  # type: ignore[arg-type]
        )
        for u in usages
    ]


@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget_endpoint(
    budget_id: int,
    payload: BudgetUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BudgetResponse:
    user_id = _require_user_id(current_user)

    try:
        budget = get_budget_for_user(session, budget_id, user_id)
    except BudgetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        ) from exc

    budget = update_budget_amount(session, budget, payload.amount)
    return _to_response(budget)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget_endpoint(
    budget_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    user_id = _require_user_id(current_user)

    try:
        budget = get_budget_for_user(session, budget_id, user_id)
    except BudgetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        ) from exc

    delete_budget(session, budget)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
