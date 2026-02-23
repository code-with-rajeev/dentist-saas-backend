# Standard library
import uuid
from datetime import datetime

# Third-party
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Internal
from app.database.base import Base


class UserPermission(Base):
    """
    Granular permission strings assigned to staff clinic members.
    clinic_owner permissions are hardcoded in code — no rows for owners.
    Only staff rows exist here.
    """

    __tablename__ = "user_permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Whose permission this is
    clinic_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinic_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Denormalized for fast clinic-scoped queries
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # e.g. "appointment:write", "patient:read"
    permission: Mapped[str] = mapped_column(String(100), nullable=False)

    # Audit trail
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinic_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )

    # Relationship back to clinic_member
    clinic_member: Mapped["ClinicMember"] = relationship(
        "ClinicMember",
        foreign_keys=[clinic_member_id],
        back_populates="permissions",
    )

    def __repr__(self) -> str:
        return f"<UserPermission member={self.clinic_member_id} perm={self.permission}>"
