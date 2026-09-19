"""
API Security: Role-Based Access Control (RBAC) & Authorization Layer.

Enforces least-privilege access control on Dhwani backend endpoints.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Dict, List, Set

from fastapi import Depends, HTTPException, status

from .authentication import get_current_user


class Role(str, Enum):
    """System roles representing distinct actors in Dhwani."""
    CLIENT = "client"        # Mobile app or edge client submitting audio streams
    ANALYST = "analyst"      # Security analyst reviewing call alerts and risk trends
    AUDITOR = "auditor"      # Forensic auditor inspecting hash chains and certificates
    ADMIN = "admin"          # Security administrator with full management access


class Permission(str, Enum):
    """Granular permissions governing specific operations."""
    AUDIO_ANALYZE = "audio:analyze"
    SESSION_READ = "session:read"
    AUDIT_READ = "audit:read"
    AUDIT_VERIFY = "audit:verify"
    AUDIT_CHECKPOINT = "audit:checkpoint"
    AUDIO_DECRYPT = "audio:decrypt"
    RETENTION_MANAGE = "retention:manage"
    ADMIN_ALL = "admin:all"


# Default permission matrix mapping roles to standard permissions
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.CLIENT: {
        Permission.AUDIO_ANALYZE,
        Permission.SESSION_READ,
    },
    Role.ANALYST: {
        Permission.AUDIO_ANALYZE,
        Permission.SESSION_READ,
        Permission.AUDIT_READ,
    },
    Role.AUDITOR: {
        Permission.AUDIT_READ,
        Permission.AUDIT_VERIFY,
        Permission.AUDIT_CHECKPOINT,
    },
    Role.ADMIN: {
        Permission.AUDIO_ANALYZE,
        Permission.SESSION_READ,
        Permission.AUDIT_READ,
        Permission.AUDIT_VERIFY,
        Permission.AUDIT_CHECKPOINT,
        Permission.AUDIO_DECRYPT,
        Permission.RETENTION_MANAGE,
        Permission.ADMIN_ALL,
    },
}


class AuthorizationError(Exception):
    """Raised when an actor lacks permission for an operation."""
    pass


def user_has_permission(user: Dict[str, Any], required_perm: str) -> bool:
    """
    Evaluates whether a user entity satisfies a required permission,
    checking both explicitly granted JWT scopes and inherited role permissions.
    """
    user_role_str = user.get("role", "")
    try:
        user_role = Role(user_role_str)
    except ValueError:
        user_role = None

    # Admin role possesses all permissions
    if user_role == Role.ADMIN:
        return True

    # Check explicit scopes in token
    token_scopes = set(user.get("scopes", []))
    if Permission.ADMIN_ALL.value in token_scopes or required_perm in token_scopes:
        return True

    # Check role-inherited permissions
    if user_role and user_role in ROLE_PERMISSIONS:
        inherited = {p.value for p in ROLE_PERMISSIONS[user_role]}
        if required_perm in inherited:
            return True

    return False


def require_role(*allowed_roles: str | Role) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """
    FastAPI dependency factory enforcing that the authenticated user
    possesses at least one of the specified roles.
    """
    normalized_roles = {r.value if isinstance(r, Role) else str(r) for r in allowed_roles}

    async def _role_verifier(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = user.get("role", "")
        # Admin is permitted on any role requirement
        if user_role == Role.ADMIN.value or user_role in normalized_roles:
            return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: User role '{user_role}' lacks required role among {list(normalized_roles)}.",
        )

    return _role_verifier


def require_permission(*required_permissions: str | Permission) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """
    FastAPI dependency factory enforcing that the authenticated user
    possesses all specified granular permissions.
    """
    normalized_perms = [p.value if isinstance(p, Permission) else str(p) for p in required_permissions]

    async def _permission_verifier(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        missing = [p for p in normalized_perms if not user_has_permission(user, p)]
        if not missing:
            return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Lacks required permission(s): {missing}.",
        )

    return _permission_verifier
