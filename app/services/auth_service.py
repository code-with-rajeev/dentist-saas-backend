# Standard library
import uuid
from datetime import datetime, timezone

# Third-party
from sqlalchemy.ext.asyncio import AsyncSession

# Internal — core
from app.core.exceptions import AuthException, ConflictException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.constants.messages import (
    EMAIL_ALREADY_EXISTS,
    INVALID_CREDENTIALS,
    ACCOUNT_INACTIVE,
    REFRESH_TOKEN_INVALID,
)
from app.constants.roles import MemberRole

# Internal — repositories
from app.repositories.clinic_repository import ClinicRepository
from app.repositories.user_repository import UserRepository

# Internal — RBAC
from app.rbac.roles import OWNER_PERMISSIONS

# Internal — schemas
from app.schemas.auth import (
    MeResponse,
    RegisterRequest,
    RegisterResponse,
    ClinicResponse,
    TokenResponse,
    UserResponse,
)
from app.rbac.current_user import CurrentUser


class AuthService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.clinic_repo = ClinicRepository(db)

    # ------------------------------------------------------------------
    # Register
    # ------------------------------------------------------------------
    async def register_clinic(self, data: RegisterRequest) -> RegisterResponse:
        """
        Atomic: creates user + clinic + clinic_member (owner) in one transaction.
        On any error, the entire transaction rolls back.
        """
        # 1. Guard: email must be unique
        if await self.user_repo.exists_by_email(data.email):
            raise ConflictException(
                code=EMAIL_ALREADY_EXISTS,
                message="An account with this email already exists",
            )

        # 2. Create user
        user = await self.user_repo.create(
            email=data.email,
            hashed_password=hash_password(data.password),
        )

        # 3. Create clinic
        clinic = await self.clinic_repo.create(
            name=data.clinic_name,
            dentist_name=data.dentist_name,
            dentist_reg_id=data.dentist_reg_id,
        )

        # 4. Create clinic_member (owner)
        member = await self.clinic_repo.create_member(
            user_id=user.id,
            clinic_id=clinic.id,
            full_name=data.full_name,
            phone=data.phone,
            role=MemberRole.CLINIC_OWNER.value,
            is_active=True,
        )

        # 5. Build JWT (owner permissions hardcoded — no DB rows needed)
        access_token = _build_access_token(user, member, clinic.id)

        return RegisterResponse(
            user=UserResponse(
                id=member.id,
                email=user.email,
                full_name=member.full_name,
                role=member.role,
                clinic_id=clinic.id,
                permissions=list(OWNER_PERMISSIONS),
                is_active=member.is_active,
            ),
            clinic=ClinicResponse(
                id=clinic.id,
                name=clinic.name,
                dentist_name=clinic.dentist_name,
                status=clinic.status,
            ),
            access_token=access_token,
            token_type="bearer",
        )

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    async def login(self, email: str, password: str) -> tuple[str, str]:
        """
        Returns (access_token, refresh_token).
        Caller stores refresh_token in HttpOnly cookie.
        """
        # 1. Load user
        user = await self.user_repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthException(
                code=INVALID_CREDENTIALS,
                message="Invalid email or password",
            )

        # 2. Check account active
        if not user.is_active:
            raise AuthException(
                code=ACCOUNT_INACTIVE,
                message="Account is deactivated. Contact clinic owner.",
            )

        # 3. Load clinic membership
        member = await _get_member_for_user(self.clinic_repo, user.id)
        if member is None:
            raise AuthException(
                code=INVALID_CREDENTIALS,
                message="Invalid email or password",
            )

        # 4. Check member active
        if not member.is_active:
            raise AuthException(
                code=ACCOUNT_INACTIVE,
                message="Account is deactivated. Contact clinic owner.",
            )

        # 5. Load permissions
        permissions = _load_permissions(member)

        # 6. Build tokens
        access_token = _build_access_token(user, member, member.clinic_id, permissions)
        refresh_token = create_refresh_token({
            "sub": str(member.id),
            "clinic_id": str(member.clinic_id),
        })

        # 7. Update last login (fire and forget within same transaction)
        await self.user_repo.update_last_login(user.id)

        return access_token, refresh_token

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------
    async def refresh_access_token(self, refresh_token: str) -> str:
        """Validate refresh token and issue a new access token."""
        payload = decode_refresh_token(refresh_token)  # raises if invalid/expired

        try:
            member_id = uuid.UUID(payload["sub"])
            clinic_id = uuid.UUID(payload["clinic_id"])
        except (KeyError, ValueError):
            raise AuthException(
                code=REFRESH_TOKEN_INVALID,
                message="Invalid refresh token",
            )

        # Re-load member and user to get fresh state
        member = await self.clinic_repo.get_member_by_id(member_id, clinic_id)
        if member is None or not member.is_active:
            raise AuthException(
                code=ACCOUNT_INACTIVE,
                message="Account is deactivated",
            )

        user = await self.user_repo.get_by_id(member.user_id)
        if user is None or not user.is_active:
            raise AuthException(
                code=ACCOUNT_INACTIVE,
                message="Account is deactivated",
            )

        permissions = _load_permissions(member)
        return _build_access_token(user, member, clinic_id, permissions)

    # ------------------------------------------------------------------
    # Me
    # ------------------------------------------------------------------
    async def get_me(self, current_user: CurrentUser) -> MeResponse:
        """Return full profile for the /me endpoint."""
        member = await self.clinic_repo.get_member_by_id(
            current_user.id, current_user.clinic_id
        )
        user = await self.user_repo.get_by_id(current_user.user_id)
        clinic = await self.clinic_repo.get_by_id(current_user.clinic_id)

        return MeResponse(
            id=member.id,
            user_id=user.id,
            full_name=member.full_name,
            email=user.email,
            role=member.role,
            clinic_id=clinic.id,
            clinic_name=clinic.name,
            permissions=_load_permissions(member),
            is_active=member.is_active,
            last_login_at=user.last_login_at,
        )
    # change password
    async def change_password(self, current_user: CurrentUser, old_password: str, new_password: str) -> None:
        """Change password for the current user."""
        user = await self.user_repo.get_by_id(current_user.user_id)
        if user is None or not verify_password(old_password, user.hashed_password):
            raise AuthException(
                code=INVALID_CREDENTIALS,
                message="Invalid current password.",
            )

        await self.user_repo.update_password(
            user_id=user.id,
            new_hashed_password=hash_password(new_password),
        )


# ============================================================
# Private helpers
# ============================================================

def _load_permissions(member) -> list[str]:
    """Hardcode for owner; load from DB rows for staff."""
    if member.role == MemberRole.CLINIC_OWNER.value:
        return list(OWNER_PERMISSIONS)
    return [p.permission for p in (member.permissions or [])]


def _build_access_token(user, member, clinic_id, permissions=None) -> str:
    if permissions is None:
        permissions = _load_permissions(member)
    return create_access_token({
        "sub": str(member.id),
        "user_id": str(user.id),
        "clinic_id": str(clinic_id),
        "full_name": member.full_name,
        "role": member.role,
        "permissions": permissions,
        "is_active": member.is_active,
    })


async def _get_member_for_user(clinic_repo: ClinicRepository, user_id: uuid.UUID):
    """Find the first active clinic_member for a given user_id."""
    # In MVP: one user = one clinic. In post-MVP: multi-clinic requires clinic selection.
    from sqlalchemy import select
    from app.models.clinic_member import ClinicMember
    from sqlalchemy.orm import selectinload

    result = await clinic_repo.db.execute(
        select(ClinicMember)
        .where(
            ClinicMember.user_id == user_id,
            ClinicMember.deleted_at.is_(None),
        )
        .options(selectinload(ClinicMember.permissions))
        .limit(1)
    )
    return result.scalar_one_or_none()
