# Standard library
import uuid
from datetime import date, time

# Third-party
from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    Time,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Internal
from app.database.base import Base
from app.database.mixins import TimestampMixin


class Appointment(Base, TimestampMixin):
    """
    Central table — every appointment ever booked in a clinic.
    Status transitions enforced at the service layer via state machine.
    No soft delete — status=cancelled/no_show serves as the 'delete'.
    """

    __tablename__ = "appointments"

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
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Human-readable display ID — Format: APT-YYYY-NNNNN
    appointment_code: Mapped[str] = mapped_column(String(20), nullable=False)

    # Type and follow-up linkage
    appointment_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="new",
    )
    parent_appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Status — see AppointmentStatus enum + state machine in constants/appointment.py
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    queue_position: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,   # only set when status = waiting
    )

    # Scheduling
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    scheduled_time_slot: Mapped[time] = mapped_column(Time, nullable=False)

    # Pre-consultation notes (set by assistant at booking)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Cancellation tracking
    cancelled_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Audit trail — who did what
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinic_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinic_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinic_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    confirmed_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient",
        foreign_keys=[patient_id],
        back_populates="appointments",
    )
    consultation: Mapped["Consultation | None"] = relationship(
        "Consultation",
        back_populates="appointment",
        uselist=False,
        lazy="selectin",
    )

    __table_args__ = (
        Index("uq_appointments_code_clinic", "clinic_id", "appointment_code", unique=True),
        Index("idx_appointments_clinic_date", "clinic_id", "scheduled_date"),
        Index("idx_appointments_patient", "patient_id", "clinic_id"),
        Index("idx_appointments_status", "clinic_id", "status", "scheduled_date"),
    )

    def __repr__(self) -> str:
        return f"<Appointment id={self.id} code={self.appointment_code} status={self.status}>"
