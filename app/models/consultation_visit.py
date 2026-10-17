# Standard library
import uuid

# Third-party
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, SmallInteger, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Internal
from app.database.base import Base
from app.database.mixins import TimestampMixin


class ConsultationVisit(Base, TimestampMixin):
    """
    One visit = one day = one appointment.
    Always finalized same day — is_finalized=True means LOCKED.
    Replaces the old Consultation model.
    Branches live in ConsultationBranch — one per case/complaint.
    """

    __tablename__ = "consultation_visits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="RESTRICT"), nullable=False)
    appointment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="RESTRICT"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False)
    dentist_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinic_members.id", ondelete="RESTRICT"), nullable=False)

    # Visit-level state
    is_finalized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    finalized_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Billing summary — computed from branches on finalize
    total_billed: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.00, server_default="0.00")
    total_paid: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.00, server_default="0.00")

    # Follow-up (visit level — covers all branches)
    is_follow_up_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    follow_up_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_days: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # PDF report
    report_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    report_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    report_generated_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    branches: Mapped[list["ConsultationBranch"]] = relationship(
        "ConsultationBranch",
        back_populates="visit",
        cascade="all, delete-orphan",
        order_by="ConsultationBranch.created_at",
        lazy="selectin",
    )
    follow_up: Mapped["FollowUp | None"] = relationship(
        "FollowUp",
        back_populates="visit",
        uselist=False,
    )
    appointment: Mapped["Appointment"] = relationship(
        "Appointment",
        back_populates="visit",
        foreign_keys=[appointment_id],
    )

    __table_args__ = (
        Index("uq_visit_appointment", "appointment_id", unique=True),
        Index("idx_visit_clinic", "clinic_id"),
        Index("idx_visit_patient", "patient_id", "clinic_id"),
        Index("idx_visit_finalized", "clinic_id", "is_finalized"),
    )

    def __repr__(self) -> str:
        return f"<ConsultationVisit id={self.id} finalized={self.is_finalized}>"