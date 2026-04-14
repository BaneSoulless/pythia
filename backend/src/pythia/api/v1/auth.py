"""
Authentication API Endpoints

Provides registration, login (access + refresh tokens), token refresh, and user info.
"""

import structlog
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from pydantic import BaseModel, EmailStr
from pythia.core.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    decode_token,
    get_current_active_user,
)
from pythia.core.config import settings
from pythia.infrastructure.persistence.database import get_db
from pythia.infrastructure.persistence.models import User
from sqlalchemy.orm import Session

router = APIRouter()
logger = structlog.get_logger(__name__)


class UserCreate(BaseModel):
    """User registration request model."""

    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response model."""

    id: int
    username: str
    email: str
    is_active: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Token pair response model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    """Refresh token request model."""

    refresh_token: str


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    - **username**: Unique username
    - **email**: User email address
    - **password**: User password (will be hashed)
    """
    try:
        user = create_user(db, user_data.username, user_data.email, user_data.password)
        logger.info("user_registered", username=user.username)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    Authenticate and receive access + refresh token pair.

    - **username**: Username or email
    - **password**: User password
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.username})

    logger.info("user_logged_in", username=user.username)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information. Requires valid JWT access token."""
    return current_user


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(body: RefreshRequest):
    """
    Exchange a valid refresh token for a new access + refresh token pair.

    Does NOT require the Authorization header.
    """
    try:
        payload = decode_token(body.refresh_token, expected_type="refresh")
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from None

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    new_refresh = create_refresh_token(data={"sub": username})

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
