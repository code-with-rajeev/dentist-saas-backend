# Standard library
import uuid
from typing import Annotated

# Third-party
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Internal — core
from app.core.exceptions import AuthException, ForbiddenException
from app.core.security import decode_access_token
from app.constants.messages import (
    UNAUTHORIZED,
    FORBIDDEN,
    ACCOUNT_INACTIVE,
    CLINIC_ACCESS_DENIED,
    OWNER_ROLE_REQUIRED,
)
from app.constants.roles import MemberRole
from app.rbac.current_user import CurrentUser
from app.rbac.permissions import ALL_PERMISSIONS, OWNER_EXCLUSIVE_PERMISSIONS
from app.rbac.roles import OWNER_PERMISSIONS

# ============================================================
# Bearer token extractor
# ============================================================
_bearer = HTTPBearer(auto_error=False)


def _extract_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    """Pull the raw token string from the Authorization header."""
    if credentials is None or not credentials.credentials:
        raise AuthException(
            code=UNAUTHORIZED,
            message="Authentication required",
        )
    return credentials.credentials


# ============================================================
# Core user loader — called by all downstream dependencies
# ============================================================
def get_current_user(
    token: Annotated[str, Depends(_extract_token)],
) -> CurrentUser:
    """
    Validates the JWT access token and returns a CurrentUser.

    Token payload structure (set at login):
    {
        "sub": "<clinic_member_id>",
        "user_id": "<user_id>",
        "clinic_id": "<clinic_id>",
        "full_name": "Dr. Arjun Mehta",
        "role": "clinic_owner",
        "permissions": ["appointment:read", ...],
        "type": "access",
        "exp": <timestamp>
    }

    For clinic_owner: permissions in payload = OWNER_PERMISSIONS (all 12).
    For staff: permissions in payload = their DB-stored permission strings.
    """
    payload = decode_access_token(token)  # raises AuthException on invalid/expired

    try:
        member_id = uuid.UUID(payload["sub"])
        user_id = uuid.UUID(payload["user_id"])
        clinic_id = uuid.UUID(payload["clinic_id"])
        full_name = payload["full_name"]
        role = payload["role"]
        is_active = payload.get("is_active", True)

        # For owner: always use hardcoded full list to avoid stale tokens
        if role == MemberRole.CLINIC_OWNER.value:
            permissions = list(OWNER_PERMISSIONS)
        else:
            permissions = payload.get("permissions", [])

    except (KeyError, ValueError) as exc:
        raise AuthException(
            code=UNAUTHORIZED,
            message="Invalid token payload",
            detail=str(exc),
        )

    if not is_active:
        raise AuthException(code=ACCOUNT_INACTIVE, message="Account is inactive")

    return CurrentUser(
        id=member_id,
        user_id=user_id,
        clinic_id=clinic_id,
        full_name=full_name,
        role=role,
        permissions=permissions,
        is_active=is_active,
    )


# Annotated type alias for clean route signatures
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]


# ============================================================
# Permission-based dependency factories
# ============================================================
def require_permission(permission: str):
    """
    Returns a FastAPI dependency that:
    1. Validates the JWT → gets CurrentUser
    2. Checks the user has the required permission

    Usage:
        @router.get("/appointments", dependencies=[Depends(require_permission("appointment:read"))])
        async def list_appointments(current_user: AuthenticatedUser): ...
    """
    def _check(current_user: AuthenticatedUser) -> CurrentUser:
        if not current_user.has_permission(permission):
            raise ForbiddenException(
                code=FORBIDDEN,
                message="You don't have permission to perform this action",
                detail=f"Required permission: {permission}",
            )
        return current_user
    return _check


def require_permissions(permissions: list[str]):
    """
    Returns a FastAPI dependency that requires ALL listed permissions.
    """
    def _check(current_user: AuthenticatedUser) -> CurrentUser:
        if not current_user.has_all_permissions(permissions):
            missing = [p for p in permissions if not current_user.has_permission(p)]
            raise ForbiddenException(
                code=FORBIDDEN,
                message="You don't have permission to perform this action",
                detail=f"Missing permissions: {missing}",
            )
        return current_user
    return _check


def require_owner():
    """
    Returns a FastAPI dependency that requires the user to be clinic_owner.
    Used for routes where the role check matters (not just permissions).

    Usage:
        @router.delete("/clinic/staff/{id}", dependencies=[Depends(require_owner())])
    """
    def _check(current_user: AuthenticatedUser) -> CurrentUser:
        if not current_user.is_owner:
            raise ForbiddenException(
                code=OWNER_ROLE_REQUIRED,
                message="This action requires clinic owner role",
            )
        return current_user
    return _check


def require_clinic_scope(clinic_id: uuid.UUID, current_user: CurrentUser) -> None:
    """
    Utility function (NOT a dependency) to verify a resource belongs to
    the current user's clinic. Call inside service or route functions.

    Usage:
        require_clinic_scope(patient.clinic_id, current_user)
    """
    if clinic_id != current_user.clinic_id:
        raise ForbiddenException(
            code=CLINIC_ACCESS_DENIED,
            message="Access denied — resource belongs to a different clinic",
        )
