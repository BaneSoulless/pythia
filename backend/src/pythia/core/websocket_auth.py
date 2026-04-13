"""
WebSocket Authentication Middleware
Implements: JWT-based authentication for WebSocket connections
"""

import logging

from fastapi import WebSocket, status
from jose import JWTError, jwt

from pythia.core.config import settings
from pythia.infrastructure.persistence.database import get_db
from pythia.infrastructure.persistence.models import User

logger = logging.getLogger(__name__)


async def authenticate_websocket(websocket: WebSocket) -> User | None:
    """
    Authenticate WebSocket connection via JWT token.

    SECURITY FIX: Prevents unauthorized access to real-time portfolio data.

    Token can be provided via:
    1. Query parameter: ?token=<jwt>
    2. Header: Authorization: Bearer <jwt>

    Returns:
        User object if authenticated, None otherwise (connection closed)
    """
    try:
        # Try query parameter first
        token = websocket.query_params.get("token")

        # Fallback to Authorization header
        if not token:
            auth_header = websocket.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if not token:
            logger.warning("websocket_auth_failed", reason="no_token")
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required"
            )
            return None

        # Verify JWT
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            user_id = payload.get("sub")

            if not user_id:
                logger.warning("websocket_auth_failed", reason="invalid_token_payload")
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token"
                )
                return None

        except JWTError as e:
            logger.warning(
                "websocket_auth_failed", reason="jwt_decode_error", error=str(e)
            )
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token"
            )
            return None

        # Fetch user from database
        db = next(get_db())
        try:
            user = db.query(User).filter(User.id == int(user_id)).first()

            if not user:
                logger.warning(
                    "websocket_auth_failed", reason="user_not_found", user_id=user_id
                )
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION, reason="User not found"
                )
                return None

            if not user.is_active:
                logger.warning(
                    "websocket_auth_failed", reason="user_inactive", user_id=user_id
                )
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION, reason="User inactive"
                )
                return None

            logger.info(
                "websocket_authenticated", user_id=user.id, username=user.username
            )
            return user

        finally:
            db.close()

    except Exception as e:
        logger.error("websocket_auth_error", error=str(e), exc_info=True)
        await websocket.close(
            code=status.WS_1011_INTERNAL_ERROR, reason="Authentication error"
        )
        return None


async def verify_portfolio_ownership(
    user: User, portfolio_id: int
) -> bool:
    """
    Verify that user owns the requested portfolio.

    Returns:
        True if authorized, False otherwise
    """
    from pythia.infrastructure.persistence.database import get_db
    from pythia.infrastructure.persistence.models import Portfolio

    db = next(get_db())
    try:
        portfolio = (
            db.query(Portfolio)
            .filter(Portfolio.id == portfolio_id, Portfolio.user_id == user.id)
            .first()
        )

        if not portfolio:
            logger.warning(
                "websocket_authorization_failed",
                user_id=user.id,
                portfolio_id=portfolio_id,
                reason="portfolio_not_owned",
            )
            return False

        return True
    finally:
        db.close()
