from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import create_access_token, set_auth_cookie
from app.models.entities import User
from app.schemas.auth import AuthResponse, LoginRequest, ProfileResponse, RegisterRequest
from app.services.password_service import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def to_profile_response(user: User) -> ProfileResponse:
    if user.id is None:
        raise ValueError("User ID must be set")

    return ProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        currency=user.currency,
        timezone=user.timezone,
        locale=user.locale,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    session: Session = Depends(get_session),
) -> AuthResponse:
    existing_user = session.exec(select(User).where(User.email == payload.email)).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        currency=payload.currency,
        timezone=payload.timezone,
        locale=payload.locale,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    return AuthResponse(user=to_profile_response(user))


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
) -> AuthResponse:
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid user profile",
        )

    access_token = create_access_token(user_id=user.id, email=user.email)
    set_auth_cookie(response, access_token)

    return AuthResponse(user=to_profile_response(user))
