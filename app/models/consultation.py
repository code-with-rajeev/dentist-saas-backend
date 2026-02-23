# Standard library
import uuid

# Third-party
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, SmallInteger, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Internal
from app.database.base import Base
from app.database.mixins import TimestampMixin


class Consultation(Base, TimestampMixin):
    """
    Clinical notes filled by dentist per appointment.
    One consultation per appointment (unique FK enforced by index).
    Locked after submission — is_submitted=True means no further edits.
    """

    __tablename__ = "consultations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # One-to-one with Appointment — enforced by unique index below
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # FK to clinic_members — the dentist who filled the form
    dentist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinic_members.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Clinical data
    symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)
    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(
        Text, nullable=True   # POST-MVP: structured JSONB with ICD codes
    )

    # Financials — DECIMAL(10, 2) supports up to 99,999,999.99
    fee_charged: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0.00,
        server_default="0.00",
    )

    # Follow-up
    is_follow_up_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    follow_up_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_days: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # Form state — is_submitted=True means LOCKED
    is_submitted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    submitted_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # PDF report
    report_generated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    report_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True   # local path in MVP; S3 key post-MVP
    )
    report_generated_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    appointment: Mapped["Appointment"] = relationship(
        "Appointment",
        back_populates="consultation",
        foreign_keys=[appointment_id],
    )
    medications: Mapped[list["Medication"]] = relationship(
        "Medication",
        back_populates="consultation",
        cascade="all, delete-orphan",
        order_by="Medication.sort_order",
        lazy="selectin",
    )
    follow_up: Mapped["FollowUp | None"] = relationship(
        "FollowUp",
        back_populates="consultation",
        uselist=False,
    )

    __table_args__ = (
        # One consultation per appointment
        Index("uq_consultations_appointment", "appointment_id", unique=True),
        Index("idx_consultations_clinic", "clinic_id"),
        Index("idx_consultations_patient", "patient_id", "clinic_id"),
        Index("idx_consultations_dentist", "dentist_id"),
        Index("idx_consultations_submitted", "clinic_id", "is_submitted"),
    )

    def __repr__(self) -> str:
        return f"<Consultation id={self.id} submitted={self.is_submitted}>"
