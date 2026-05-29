from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.logging import get_logger
from app.core.security import clear_auth_cookie, create_access_token, set_auth_cookie
from app.dependencies.auth import get_current_user
from app.models.entities import User
from app.schemas.auth import AuthResponse, LoginRequest, ProfileResponse, RegisterRequest
from app.services.audit import record_audit_event
from app.services.password_service import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


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
    response: Response,
    session: Session = Depends(get_session), 
) -> AuthResponse:
    logger.info("Register attempt for email: %s", payload.email)
    
    try:
        logger.debug("Checking if user exists...")
        existing_user = session.exec(select(User).where(User.email == payload.email)).first()
        if existing_user is not None:
            logger.warning("Email already registered: %s", payload.email)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        logger.debug("Hashing password...")
        password_hash = hash_password(payload.password)
        
        logger.debug("Creating user...")
        user = User(
            email=payload.email,
            password_hash=password_hash,
            full_name=payload.full_name,
            currency=payload.currency,
            timezone=payload.timezone,
            locale=payload.locale,
        )
        session.add(user)
        
        logger.debug("Committing to database...")
        session.commit()
        session.refresh(user)
        logger.info("User created successfully: %s", user.email)

        if user.id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid user profile",
            )

        record_audit_event(
            session,
            user_id=user.id,
            event="auth.register",
            target_type="user",
            target_id=user.id,
            commit=True,
        )

        logger.debug("Creating access token...")
        access_token = create_access_token(user_id=user.id, email=user.email)
        set_auth_cookie(response, access_token)

        logger.info("Registration successful for: %s", user.email)
        return AuthResponse(user=to_profile_response(user))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Registration failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        ) from e


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

    record_audit_event(
        session,
        user_id=user.id,
        event="auth.login",
        target_type="user",
        target_id=user.id,
        commit=True,
    )

    access_token = create_access_token(user_id=user.id, email=user.email)
    set_auth_cookie(response, access_token)

    return AuthResponse(user=to_profile_response(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    clear_auth_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=AuthResponse)
def get_me(current_user: User = Depends(get_current_user)) -> AuthResponse:
    return AuthResponse(user=to_profile_response(current_user))
