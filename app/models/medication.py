# Standard library
import uuid
from datetime import datetime, timezone

# Third-party
from sqlalchemy import DateTime, ForeignKey, SmallInteger, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Internal
from app.database.base import Base


class Medication(Base):
    """
    Prescriptions within a consultation branch.
    Deleted with branch (CASCADE).
    """

    __tablename__ = "medications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("consultation_branches.id", ondelete="CASCADE"),
        nullable=False,
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="RESTRICT"), nullable=False)
    med_library_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("med_library.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    branch: Mapped["ConsultationBranch"] = relationship(
        "ConsultationBranch",
        back_populates="medications",
        foreign_keys=[branch_id],
    )

    __table_args__ = (
        Index("idx_medications_branch", "branch_id"),
        Index("idx_medications_clinic", "clinic_id"),
    )

    def __repr__(self) -> str:
        return f"<Medication id={self.id} name={self.name}>"