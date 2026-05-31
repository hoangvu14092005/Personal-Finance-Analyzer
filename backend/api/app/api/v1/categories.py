"""Category APIs (Phase 3.4 / 3.6 — supporting M4 UI; G1 — CRUD).

- `GET /categories`: list system + user-owned categories.
- `POST /categories`: tạo category của user.
- `PATCH /categories/{id}`: sửa category của chính user (chặn system).
- `DELETE /categories/{id}`: xóa category của user; transaction đang dùng được
  set `category_id=NULL` thay vì xóa transaction.
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, col, or_, select

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import Category, Transaction, User
from app.schemas.categories import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
)

router = APIRouter(prefix="/categories", tags=["categories"])


def _require_user_id(current_user: User) -> int:
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )
    return current_user.id


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


def _get_owned_category(session: Session, category_id: int, user_id: int) -> Category:
    """Lấy category thuộc về user. Chặn system + category của user khác."""
    category = session.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if category.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System categories cannot be modified",
        )
    if category.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


@router.get("", response_model=CategoryListResponse)
def list_categories(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CategoryListResponse:
    user_id = _require_user_id(current_user)

    statement = (
        select(Category)
        .where(
            or_(
                col(Category.is_system).is_(True),
                Category.user_id == user_id,
            ),
        )
        # System trước (is_system DESC: True > False), rồi name ASC.
        .order_by(col(Category.is_system).desc(), col(Category.name).asc())
    )
    rows = session.exec(statement).all()
    return CategoryListResponse(items=[_to_response(row) for row in rows])


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    user_id = _require_user_id(current_user)
    name = payload.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name required",
        )

    # Chặn trùng tên với category hệ thống hoặc category đã có của user.
    duplicate = session.exec(
        select(Category)
        .where(Category.name == name)
        .where(
            or_(
                col(Category.is_system).is_(True),
                Category.user_id == user_id,
            ),
        ),
    ).first()
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category with this name already exists",
        )

    category = Category(
        user_id=user_id,
        name=name,
        color=payload.color,
        is_system=False,
    )
    session.add(category)
    session.commit()
    session.refresh(category)
    return _to_response(category)


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    user_id = _require_user_id(current_user)
    category = _get_owned_category(session, category_id, user_id)

    if payload.name is not None:
        new_name = payload.name.strip()
        if not new_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Name cannot be empty",
            )
        if new_name != category.name:
            duplicate = session.exec(
                select(Category)
                .where(Category.name == new_name)
                .where(
                    or_(
                        col(Category.is_system).is_(True),
                        Category.user_id == user_id,
                    ),
                ),
            ).first()
            if duplicate is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Category with this name already exists",
                )
            category.name = new_name

    if payload.color is not None:
        category.color = payload.color

    session.add(category)
    session.commit()
    session.refresh(category)
    return _to_response(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    user_id = _require_user_id(current_user)
    category = _get_owned_category(session, category_id, user_id)

    # Gỡ category khỏi transaction đang dùng (không xóa transaction).
    now = datetime.now(tz=UTC)
    for tx in session.exec(
        select(Transaction).where(Transaction.category_id == category_id),
    ):
        tx.category_id = None
        tx.updated_at = now
        session.add(tx)

    session.delete(category)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]

