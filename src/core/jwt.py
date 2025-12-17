"""
JWT Token Service
Handles creation and validation of JWT tokens for authentication
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt

from .config import get_settings

# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30  # Token valid for 30 days


def create_access_token(email: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token for a user

    Args:
        email: User email to encode in token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    settings = get_settings()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": email,  # subject (user email)
        "exp": expire,  # expiration time
        "iat": datetime.utcnow(),  # issued at
    }

    encoded_jwt = jwt.encode(to_encode, settings.app.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """
    Verify and decode a JWT token

    Args:
        token: JWT token string to verify

    Returns:
        User email if token is valid, None otherwise
    """
    settings = get_settings()

    try:
        payload = jwt.decode(token, settings.app.secret_key, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        return email
    except JWTError:
        return None


def decode_token(token: str) -> Optional[dict]:
    """
    Decode a JWT token without verification (for debugging)

    Args:
        token: JWT token string

    Returns:
        Token payload dict or None if invalid
    """
    settings = get_settings()

    try:
        payload = jwt.decode(token, settings.app.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
