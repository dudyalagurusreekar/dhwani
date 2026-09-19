"""
API Security & Access Control Module for Dhwani.
Provides client authentication (JWT / API Key), RBAC authorization, and rate limiting.
"""

from .authentication import (
    create_access_token,
    decode_access_token,
    get_current_user,
    AuthenticationError,
    JWT_SECRET_KEY,
    ALGORITHM,
)
from .authorization import (
    Role,
    Permission,
    require_role,
    require_permission,
    AuthorizationError,
)
from .rate_limiter import (
    SlidingWindowRateLimiter,
    RateLimitExceeded,
    get_rate_limiter,
)

__all__ = [
    "create_access_token",
    "decode_access_token",
    "get_current_user",
    "AuthenticationError",
    "JWT_SECRET_KEY",
    "ALGORITHM",
    "Role",
    "Permission",
    "require_role",
    "require_permission",
    "AuthorizationError",
    "SlidingWindowRateLimiter",
    "RateLimitExceeded",
    "get_rate_limiter",
]
