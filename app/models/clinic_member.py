# Standard library
import uuid
from datetime import datetime

# Third-party
from sqlalchemy import Boolean, DateTime, ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Internal
from app.database.base import Base
from app.database.mixins import TimestampMixin, SoftDeleteMixin


class ClinicMember(Base, TimestampMixin, SoftDeleteMixin):
    """
    Links a user to a clinic with a role.
    One row per user-clinic relationship.
    In MVP: a user belongs to exactly one clinic.
    Post-MVP: multiple rows = multi-clinic support.

    `full_name` and `phone` are denormalized here for fast access
    without joining to the users table on every list/queue view.
    """

    __tablename__ = "clinic_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Core relationships
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Denormalized display identity (avoids join to users on every list)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Role
    role: Mapped[str] = mapped_column(String(30), nullable=False)

    # Dentist-specific fields (null for staff)
    specialization: Mapped[str | None] = mapped_column(String(100), nullable=True)
    experience_years: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    profile_bio: Mapped[str | None] = mapped_column(Text, nullable=True)  # POST-MVP

    # Status — owner can deactivate staff without deleting
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")
    clinic: Mapped["Clinic"] = relationship("Clinic", foreign_keys=[clinic_id])
    permissions: Mapped[list["UserPermission"]] = relationship(
        "UserPermission",
        foreign_keys="[UserPermission.clinic_member_id]",
        back_populates="clinic_member",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ClinicMember id={self.id} name={self.full_name} role={self.role}>"
