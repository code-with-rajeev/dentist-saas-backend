# Standard library
import uuid
from datetime import date

# Third-party
from sqlalchemy import Date, DateTime, ForeignKey, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Internal
from app.database.base import Base
from app.database.mixins import TimestampMixin


class FollowUp(Base, TimestampMixin):
    """
    Follow-up tasks created from a consultation_visit's follow-up flag.
    Follow-up is visit-level — one per visit, covers all branches.
    In MVP: record only — status tracked manually.
    Post-MVP: triggers Celery task for WhatsApp reminder on follow_up_date.
    """

    __tablename__ = "follow_ups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="RESTRICT"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False)

    visit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("consultation_visits.id", ondelete="RESTRICT"),
        nullable=False,
    )

    follow_up_appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
    )

    follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled", server_default="scheduled")

    reminder_sent_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationship
    visit: Mapped["ConsultationVisit"] = relationship(
        "ConsultationVisit",
        back_populates="follow_up",
        foreign_keys=[visit_id],
    )

    __table_args__ = (
        Index("idx_follow_ups_clinic", "clinic_id"),
        Index("idx_follow_ups_patient", "patient_id", "clinic_id"),
        Index("idx_follow_ups_visit", "visit_id"),
        Index("idx_follow_ups_date", "clinic_id", "follow_up_date"),
    )

    def __repr__(self) -> str:
        return f"<FollowUp id={self.id} status={self.status} date={self.follow_up_date}>"
