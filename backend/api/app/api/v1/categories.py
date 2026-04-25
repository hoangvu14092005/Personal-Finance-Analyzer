"""Category APIs (Phase 3.4 / 3.6 — supporting M4 UI).

Endpoint duy nhất: `GET /api/v1/categories` trả về danh sách categories
mà user có thể chọn trong review form và manual entry form.

Scope: bao gồm cả `is_system=True` (seed mặc định) và `user_id == current_user.id`
(custom categories, sẽ làm ở phase sau). Sort:
1. System trước (để defaults luôn xuất hiện top).
2. Trong cùng nhóm sort theo `name` ASC.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, col, or_, select

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import Category, User
from app.schemas.categories import CategoryListResponse, CategoryResponse

router = APIRouter(prefix="/categories", tags=["categories"])


def _to_response(category: Category) -> CategoryResponse:
    if category.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Category id missing",
        )
    return CategoryResponse(
        id=category.id,
        name=category.name,
        color=category.color,
        is_system=category.is_system,
        user_id=category.user_id,
        created_at=category.created_at,
    )


@router.get("", response_model=CategoryListResponse)
def list_categories(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CategoryListResponse:
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )

    statement = (
        select(Category)
        .where(
            or_(
                col(Category.is_system).is_(True),
                Category.user_id == current_user.id,
            ),
        )
        # System trước (is_system DESC: True > False), rồi name ASC.
        .order_by(col(Category.is_system).desc(), col(Category.name).asc())
    )
    rows = session.exec(statement).all()
    return CategoryListResponse(items=[_to_response(row) for row in rows])
