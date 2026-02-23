# Standard library
import uuid

# Third-party
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Internal
from app.models.clinic import Clinic
from app.models.clinic_member import ClinicMember
from app.models.user_permission import UserPermission


class ClinicRepository:
    """Data access layer for clinics, clinic_members, and user_permissions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Clinic
    # ------------------------------------------------------------------
    async def get_by_id(self, clinic_id: uuid.UUID) -> Clinic | None:
        result = await self.db.execute(
            select(Clinic).where(Clinic.id == clinic_id)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> Clinic:
        clinic = Clinic(**kwargs)
        self.db.add(clinic)
        await self.db.flush()
        return clinic

    # ------------------------------------------------------------------
    # Clinic Members
    # ------------------------------------------------------------------
    async def get_member_by_user_and_clinic(
        self, user_id: uuid.UUID, clinic_id: uuid.UUID
    ) -> ClinicMember | None:
        result = await self.db.execute(
            select(ClinicMember)
            .where(
                ClinicMember.user_id == user_id,
                ClinicMember.clinic_id == clinic_id,
                ClinicMember.deleted_at.is_(None),
            )
            .options(selectinload(ClinicMember.permissions))
        )
        return result.scalar_one_or_none()

    async def get_member_by_id(
        self, member_id: uuid.UUID, clinic_id: uuid.UUID
    ) -> ClinicMember | None:
        result = await self.db.execute(
            select(ClinicMember)
            .where(
                ClinicMember.id == member_id,
                ClinicMember.clinic_id == clinic_id,
                ClinicMember.deleted_at.is_(None),
            )
            .options(selectinload(ClinicMember.permissions))
        )
        return result.scalar_one_or_none()

    async def create_member(self, **kwargs) -> ClinicMember:
        member = ClinicMember(**kwargs)
        self.db.add(member)
        await self.db.flush()
        return member

    async def get_all_active_staff(self, clinic_id: uuid.UUID) -> list[ClinicMember]:
        result = await self.db.execute(
            select(ClinicMember)
            .where(
                ClinicMember.clinic_id == clinic_id,
                ClinicMember.deleted_at.is_(None),
            )
            .options(selectinload(ClinicMember.permissions))
            .order_by(ClinicMember.created_at)
        )
        return list(result.scalars().all())

    async def soft_delete_member(self, member: ClinicMember) -> None:
        member.soft_delete()
        await self.db.flush()

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------
    async def get_permissions_by_member(
        self, member_id: uuid.UUID
    ) -> list[UserPermission]:
        result = await self.db.execute(
            select(UserPermission).where(
                UserPermission.clinic_member_id == member_id
            )
        )
        return list(result.scalars().all())

    async def replace_member_permissions(
        self,
        member: ClinicMember,
        new_permissions: list[str],
        granted_by_id: uuid.UUID,
        clinic_id: uuid.UUID,
    ) -> list[UserPermission]:
        """Delete all existing permissions and insert new ones atomically."""
        # Remove old
        for perm in member.permissions:
            await self.db.delete(perm)
        await self.db.flush()

        # Insert new
        created = []
        for perm_str in new_permissions:
            perm = UserPermission(
                clinic_member_id=member.id,
                clinic_id=clinic_id,
                permission=perm_str,
                granted_by=granted_by_id,
            )
            self.db.add(perm)
            created.append(perm)

        await self.db.flush()
        return created

    async def create_permissions(
        self,
        member_id: uuid.UUID,
        clinic_id: uuid.UUID,
        permissions: list[str],
        granted_by_id: uuid.UUID | None = None,
    ) -> list[UserPermission]:
        created = []
        for perm_str in permissions:
            perm = UserPermission(
                clinic_member_id=member_id,
                clinic_id=clinic_id,
                permission=perm_str,
                granted_by=granted_by_id,
            )
            self.db.add(perm)
            created.append(perm)
        await self.db.flush()
        return created
