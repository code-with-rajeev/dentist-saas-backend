# Standard library
from datetime import datetime, timedelta, timezone
from typing import Any

# Third-party
from jose import JWTError, jwt
from passlib.context import CryptContext

# Internal
from app.core.config import settings
from app.core.exceptions import AuthException
from app.constants.messages import TOKEN_EXPIRED, TOKEN_INVALID, UNAUTHORIZED

# bcrypt context — only algorithm is bcrypt
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================
# Password Utilities
# ============================================================

def hash_password(plain_password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


# ============================================================
# JWT Utilities
# ============================================================

def create_access_token(data: dict[str, Any]) -> str:
    """
    Create a short-lived JWT access token.
    Expiry: JWT_ACCESS_TOKEN_EXPIRE_MINUTES (default 15 min).
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload.update({"exp": expire, "type": "access"})
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Create a long-lived JWT refresh token.
    Expiry: JWT_REFRESH_TOKEN_EXPIRE_DAYS (default 7 days).
    Stored in HttpOnly cookie — never in response body.
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload.update({"exp": expire, "type": "refresh"})
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.
    Raises AuthException on invalid or expired tokens.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as exc:
        error_msg = str(exc).lower()
        if "expired" in error_msg:
            raise AuthException(
                code=TOKEN_EXPIRED,
                message="Session expired, please login again",
                detail=str(exc),
            )
        raise AuthException(
            code=TOKEN_INVALID,
            message="Invalid token",
            detail=str(exc),
        )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode access token and verify it is of type 'access'."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise AuthException(
            code=UNAUTHORIZED,
            message="Authentication required",
        )
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode refresh token and verify it is of type 'refresh'."""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise AuthException(
            code=TOKEN_INVALID,
            message="Invalid token",
        )
    return payload
