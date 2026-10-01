"""Registration and login endpoints."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import Database
from app.core.rate_limit import login_limiter, register_limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserProfileRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserProfileRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Database):
    settings = get_settings()
    if settings.environment != "test":
        allowed, retry_after = register_limiter.allow(request.client.host if request.client else "unknown")
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de tentatives. Réessayez plus tard.",
                headers={"Retry-After": str(retry_after)},
            )
    email = str(payload.email).casefold()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette adresse est déjà utilisée.")
    user = User(email=email, password_hash=hash_password(payload.password), display_name=payload.display_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Database):
    settings = get_settings()
    if settings.environment != "test":
        allowed, retry_after = login_limiter.allow(request.client.host if request.client else "unknown")
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de tentatives. Réessayez plus tard.",
                headers={"Retry-After": str(retry_after)},
            )
    email = str(payload.email).casefold()
    user = db.scalar(select(User).where(User.email == email))
    # A real hash is computed even for an unknown account, reducing account
    # enumeration through timing differences.
    valid = verify_password(payload.password, user.password_hash if user else hash_password(payload.password))
    if user is None or not valid or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user.last_login_at = datetime.utcnow()
    db.add(user)
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )
