"""
Dhwani / EchoShield AI - Authentication & Authorization Framework
=================================================================
Provides API key and Bearer token authentication, environment-configurable
security enforcement, constant-time credential comparison, and WebSocket auth.
"""

import hmac
import os
from typing import Optional
from fastapi import Header, HTTPException, Query, Request, Security, WebSocket, status
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery


API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
API_KEY_QUERY = APIKeyQuery(name="api_key", auto_error=False)


def get_configured_api_key() -> Optional[str]:
    """Retrieve the master API key configured in the environment."""
    key = os.getenv("DHWANI_API_KEY", "").strip()
    return key if key else None


def is_auth_required() -> bool:
    """
    Check if authentication is mandatory.
    Returns True if DHWANI_AUTH_REQUIRED is explicitly set to 'true'/'1',
    or if DHWANI_API_KEY is configured and not empty.
    """
    explicit = os.getenv("DHWANI_AUTH_REQUIRED", "").strip().lower()
    if explicit in ("true", "1", "yes"):
        return True
    if explicit in ("false", "0", "no"):
        return False
    # If DHWANI_API_KEY is set, default to requiring authentication
    return bool(get_configured_api_key())


def validate_api_key(provided_key: Optional[str]) -> bool:
    """
    Validate provided credential against configured key using constant-time comparison.
    """
    configured = get_configured_api_key()
    if not configured:
        # If no key configured and auth not strictly required, allow
        return not is_auth_required()

    if not provided_key:
        return False

    return hmac.compare_digest(provided_key.strip(), configured)


async def require_api_key(
    request: Request,
    x_api_key: Optional[str] = Security(API_KEY_HEADER),
) -> Optional[str]:
    """
    FastAPI dependency for protected REST routes.
    Accepts credentials via:
    1. 'X-API-Key' header
    2. 'Authorization: Bearer <key>' header
    """
    if not is_auth_required():
        return None

    candidate_key = x_api_key

    # Check Authorization: Bearer <token> if X-API-Key header is absent
    if not candidate_key:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            candidate_key = auth_header[7:].strip()

    if not candidate_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key missing. Provide 'X-API-Key' or 'Authorization: Bearer <token>' header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not validate_api_key(candidate_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return candidate_key


def verify_websocket_auth(websocket: WebSocket) -> bool:
    """
    Validate credentials for incoming WebSocket connections.
    Supports:
    1. Headers: 'X-API-Key', 'Authorization: Bearer <key>'
    2. Subprotocol: 'Sec-WebSocket-Protocol: token, <key>' or 'dhwani-auth, <key>'
    3. Query parameter: '?api_key=<key>' (fallback)
    """
    if not is_auth_required():
        return True

    # 1. Inspect HTTP headers first (safest, not logged in URL access logs)
    candidate_key = websocket.headers.get("X-API-Key")
    if not candidate_key:
        auth_h = websocket.headers.get("Authorization", "")
        if auth_h.startswith("Bearer "):
            candidate_key = auth_h[7:].strip()

    # 2. Inspect Sec-WebSocket-Protocol or ASGI scope for browser client authentication
    if not candidate_key:
        subproto = websocket.headers.get("sec-websocket-protocol", "")
        if subproto:
            parts = [p.strip() for p in subproto.split(",") if p.strip()]
            if len(parts) >= 2 and parts[0] in ("token", "dhwani-auth", "apikey", "bearer"):
                candidate_key = parts[1]
        if not candidate_key:
            scope_subprotos = websocket.scope.get("subprotocols", [])
            if len(scope_subprotos) >= 2 and scope_subprotos[0] in ("token", "dhwani-auth", "apikey", "bearer"):
                candidate_key = scope_subprotos[1]

    # 3. Fallback query parameter
    if not candidate_key:
        candidate_key = websocket.query_params.get("api_key") or websocket.query_params.get("token")

    return validate_api_key(candidate_key)


def get_accepted_subprotocol(websocket: WebSocket) -> Optional[str]:
    """
    Determine the safe subprotocol to accept for browser WebSocket clients.
    Returns only the protocol identifier (e.g. 'dhwani-auth') to satisfy RFC 6455
    without echoing the credential back in the response headers or logs.
    """
    subproto = websocket.headers.get("sec-websocket-protocol", "")
    if subproto:
        parts = [p.strip() for p in subproto.split(",") if p.strip()]
        if parts and parts[0] in ("dhwani-auth", "token", "apikey", "bearer"):
            return parts[0]

    scope_subprotos = websocket.scope.get("subprotocols", [])
    if scope_subprotos and scope_subprotos[0] in ("dhwani-auth", "token", "apikey", "bearer"):
        return scope_subprotos[0]

    return None
