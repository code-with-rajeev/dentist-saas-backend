# Standard library
import uuid
from datetime import datetime, timezone

# Third-party
from sqlalchemy.ext.asyncio import AsyncSession

# Internal — core
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.constants.messages import (
    CANNOT_REMOVE_OWNER,
    CLINIC_NOT_FOUND,
    EMAIL_ALREADY_EXISTS,
    INVALID_OPERATING_HOURS,
    LOCKED_FIELD_MODIFICATION,
    OWNER_EXCLUSIVE_PERMISSION,
    STAFF_NOT_FOUND,
)
from app.constants.roles import MemberRole

# Internal — repositories
from app.repositories.clinic_repository import ClinicRepository
from app.repositories.user_repository import UserRepository

# Internal — RBAC
from app.rbac.current_user import CurrentUser
from app.rbac.permissions import GRANTABLE_PERMISSIONS
from app.rbac.roles import RECOMMENDED_PERMISSIONS

# Internal — schemas
from app.schemas.clinic import (
    ClinicSettingsResponse,
    ClinicSettingsUpdate,
    StaffCreate,
    StaffPermissionsUpdate,
    StaffResponse,
)
from app.core.security import hash_password


class ClinicService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.clinic_repo = ClinicRepository(db)
        self.user_repo = UserRepository(db)

    # ------------------------------------------------------------------
    # Clinic Settings
    # ------------------------------------------------------------------
    async def get_clinic_settings(self, clinic_id: uuid.UUID) -> ClinicSettingsResponse:
        clinic = await self.clinic_repo.get_by_id(clinic_id)
        if clinic is None:
            raise NotFoundException(code=CLINIC_NOT_FOUND, message="Clinic not found")

        return ClinicSettingsResponse(
            id=clinic.id,
            name=clinic.name,
            gst_number=clinic.gst_number,
            dentist_name=clinic.dentist_name,
            dentist_reg_id=clinic.dentist_reg_id,
            phone=clinic.phone,
            email=clinic.email,
            address=clinic.address,
            city=clinic.city,
            state=clinic.state,
            pincode=clinic.pincode,
            operating_hours=clinic.operating_hours or {},
            status=clinic.status,
            subscription_plan=clinic.subscription_plan,
            locked_fields=list(clinic.LOCKED_FIELDS),
        )

    async def update_clinic_settings(
        self, clinic_id: uuid.UUID, data: ClinicSettingsUpdate
    ) -> ClinicSettingsResponse:
        clinic = await self.clinic_repo.get_by_id(clinic_id)
        if clinic is None:
            raise NotFoundException(code=CLINIC_NOT_FOUND, message="Clinic not found")

        # Apply only fields that were provided (partial update)
        update_data = data.model_dump(exclude_none=True)

        if "operating_hours" in update_data:
            # Validate hours: if day is not closed, open and close must both be present
            for day, hours in update_data["operating_hours"].items():
                hours_dict = hours if isinstance(hours, dict) else hours.model_dump()
                if not hours_dict.get("is_closed", False):
                    if not hours_dict.get("open") or not hours_dict.get("close"):
                        raise ValidationException(
                            code=INVALID_OPERATING_HOURS,
                            message=f"Operating hours for '{day}': open and close times are required when not closed",
                        )
            # Serialize OperatingHoursDay objects to dicts for JSONB storage
            update_data["operating_hours"] = {
                day: (h if isinstance(h, dict) else h.model_dump())
                for day, h in update_data["operating_hours"].items()
            }

        for field, value in update_data.items():
            setattr(clinic, field, value)

        return await self.get_clinic_settings(clinic_id)

    # ------------------------------------------------------------------
    # Staff Management
    # ------------------------------------------------------------------
    async def list_staff(self, clinic_id: uuid.UUID) -> list[StaffResponse]:
        members = await self.clinic_repo.get_all_active_staff(clinic_id)
        return [_member_to_response(m) for m in members]

    async def add_staff_member(
        self, data: StaffCreate, clinic_id: uuid.UUID, granted_by: CurrentUser
    ) -> StaffResponse:
        # Guard: email must be unique
        if await self.user_repo.exists_by_email(data.email):
            raise ConflictException(
                code=EMAIL_ALREADY_EXISTS,
                message="A user with this email already exists",
            )

        # Guard: no owner-exclusive permissions
        if data.permissions:
            bad = [p for p in data.permissions if p not in GRANTABLE_PERMISSIONS]
            if bad:
                raise ForbiddenException(
                    code=OWNER_EXCLUSIVE_PERMISSION,
                    message=f"Cannot grant owner-exclusive permissions to staff: {bad}",
                )

        # Create user
        user = await self.user_repo.create(
            email=data.email,
            hashed_password=hash_password(data.password),
        )

        # Create clinic_member
        member = await self.clinic_repo.create_member(
            user_id=user.id,
            clinic_id=clinic_id,
            full_name=data.full_name,
            phone=data.phone,
            role=data.role,
            is_active=True,
        )

        # Assign permissions (default to recommended if none provided)
        permissions = data.permissions or RECOMMENDED_PERMISSIONS.get(data.role, [])
        await self.clinic_repo.create_permissions(
            member_id=member.id,
            clinic_id=clinic_id,
            permissions=permissions,
            granted_by_id=granted_by.id,
        )

        # Reload with permissions
        member = await self.clinic_repo.get_member_by_id(member.id, clinic_id)
        member.user  # trigger eager load to populate email
        return _member_to_response(member, email=user.email)

    async def update_staff_permissions(
        self,
        staff_id: uuid.UUID,
        clinic_id: uuid.UUID,
        data: StaffPermissionsUpdate,
        granted_by: CurrentUser,
    ) -> StaffResponse:
        member = await self.clinic_repo.get_member_by_id(staff_id, clinic_id)
        if member is None:
            raise NotFoundException(code=STAFF_NOT_FOUND, message="Staff member not found")

        # Cannot change owner permissions
        if member.role == MemberRole.CLINIC_OWNER.value:
            raise ForbiddenException(
                code=OWNER_EXCLUSIVE_PERMISSION,
                message="Clinic owner permissions cannot be modified",
            )

        # Guard: no owner-exclusive permissions
        bad = [p for p in data.permissions if p not in GRANTABLE_PERMISSIONS]
        if bad:
            raise ForbiddenException(
                code=OWNER_EXCLUSIVE_PERMISSION,
                message=f"Cannot grant owner-exclusive permissions to staff: {bad}",
            )

        await self.clinic_repo.replace_member_permissions(
            member=member,
            new_permissions=data.permissions,
            granted_by_id=granted_by.id,
            clinic_id=clinic_id,
        )

        # Expire cached state so the reload fetches fresh data from DB
        await self.db.flush()
        self.db.expire(member)
        member = await self.clinic_repo.get_member_by_id(staff_id, clinic_id)
        return _member_to_response(member)

    async def remove_staff_member(
        self, staff_id: uuid.UUID, clinic_id: uuid.UUID
    ) -> None:
        member = await self.clinic_repo.get_member_by_id(staff_id, clinic_id)
        if member is None:
            raise NotFoundException(code=STAFF_NOT_FOUND, message="Staff member not found")

        # Cannot remove the owner
        if member.role == MemberRole.CLINIC_OWNER.value:
            raise ForbiddenException(
                code=CANNOT_REMOVE_OWNER,
                message="Cannot remove the clinic owner",
            )

        await self.clinic_repo.soft_delete_member(member)


# ============================================================
# Private helpers
# ============================================================

def _member_to_response(member, email: str = "") -> StaffResponse:
    """Build StaffResponse from ClinicMember ORM object."""
    # Try to get email from the eager-loaded user if not passed directly
    if not email and member.user:
        email = member.user.email

    return StaffResponse(
        id=member.id,
        full_name=member.full_name,
        email=email,
        role=member.role,
        phone=member.phone,
        is_active=member.is_active,
        permissions=[p.permission for p in (member.permissions or [])],
        created_at=member.created_at,
    )
