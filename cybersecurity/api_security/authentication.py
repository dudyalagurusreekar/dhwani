"""
API Security: Authentication Layer for Dhwani Backend.

Implements JSON Web Token (JWT) issuance, validation, and FastAPI security dependencies.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Secret key for signing JWTs (in production, set via DHWANI_JWT_SECRET environment variable)
JWT_SECRET_KEY = os.getenv(
    "DHWANI_JWT_SECRET",
    "dhwani-cryptographic-api-secret-key-production-grade-sih-2026",
)
ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60

security_bearer = HTTPBearer(auto_error=False)


class AuthenticationError(Exception):
    """Raised when authentication verification fails."""
    pass


def create_access_token(
    subject: str,
    role: str = "client",
    scopes: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Creates a signed cryptographically verifiable JWT access token.

    Args:
        subject: The unique identifier of the client, user, or service.
        role: The assigned RBAC role (e.g. 'client', 'analyst', 'auditor', 'admin').
        scopes: List of granular permission scopes granted to this token.
        expires_delta: Optional custom validity duration. Defaults to 60 minutes.
        extra_claims: Additional metadata to embed in payload.

    Returns:
        Encoded JWT token string.
    """
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "scopes": scopes or [],
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": "dhwani-auth-service",
    }

    if extra_claims:
        payload.update(extra_claims)

    encoded_jwt = jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and mathematically validates a JWT token.

    Raises:
        AuthenticationError: If the token is expired, invalid, or malformed.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iat", "sub", "role"]},
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Access token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError(f"Invalid access token: {str(exc)}") from exc


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> Dict[str, Any]:
    """
    FastAPI dependency that enforces valid Bearer JWT authentication on protected routes.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        return payload
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )
