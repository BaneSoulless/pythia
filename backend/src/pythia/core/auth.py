"""
JWT Authentication System

Provides user registration, login, JWT access + refresh token management.
SOTA 2026 - Uses timezone-aware datetime, short-lived access tokens.
"""

import structlog
from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from pythia.core.config import settings
from pythia.infrastructure.persistence.database import get_db
from pythia.infrastructure.persistence.models import User

logger = structlog.get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a short-lived JWT access token.

    Args:
        data: Claims to encode (must include 'sub').
        expires_delta: Custom TTL. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Create a long-lived refresh token.

    Args:
        data: Claims to encode (must include 'sub').

    Returns:
        Encoded JWT refresh token string.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> dict:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string.
        expected_type: Expected token type ('access' or 'refresh').

    Returns:
        Decoded payload dict.

    Raises:
        JWTError: If token is invalid, expired, or wrong type.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_type = payload.get("type", "access")
        if token_type != expected_type:
            raise JWTError(f"Expected {expected_type} token, got {token_type}")
        return payload
    except JWTError as e:
        logger.warning("jwt_decode_error", error_type=type(e).__name__)
        raise


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """
    Authenticate user with username/email and password.

    Returns:
        User object if credentials valid, None otherwise.
    """
    user = (
        db.query(User)
        .filter((User.username == username) | (User.email == username))
        .first()
    )
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency: extract current user from JWT Bearer token.

    Raises:
        HTTPException 401: If token invalid or user not found.
        HTTPException 403: If user is inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token, expected_type="access")
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception from None

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """FastAPI dependency: ensures user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def create_user(db: Session, username: str, email: str, password: str) -> User:
    """
    Create a new user with hashed password.

    Raises:
        ValueError: If username or email already registered.
    """
    if db.query(User).filter(User.username == username).first():
        raise ValueError("Username already registered")
    if db.query(User).filter(User.email == email).first():
        raise ValueError("Email already registered")

    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("user_created", username=username)
    return user
