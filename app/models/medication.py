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
    Prescriptions within a consultation.
    Multiple medications per consultation allowed.
    Deleted with consultation (CASCADE).
    """

    __tablename__ = "medications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    consultation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("consultations.id", ondelete="CASCADE"),
        nullable=False,
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Prescription details — all free text (dentist enters what they prescribe)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(100), nullable=True)    # e.g. "500mg"
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True) # e.g. "3 times a day"
    duration: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g. "5 days"
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)     # e.g. "After food"

    # Controls display order on PDF prescription
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)

    # Timestamp — created_at only (medications don't get updated, replaced instead)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    consultation: Mapped["Consultation"] = relationship(
        "Consultation",
        back_populates="medications",
        foreign_keys=[consultation_id],
    )

    __table_args__ = (
        Index("idx_medications_consultation", "consultation_id"),
        Index("idx_medications_clinic", "clinic_id"),
    )

    def __repr__(self) -> str:
        return f"<Medication id={self.id} name={self.name}>"
