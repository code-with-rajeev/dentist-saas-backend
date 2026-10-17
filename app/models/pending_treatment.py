# Standard library
import uuid

# Third-party
from sqlalchemy import Date, ForeignKey, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Internal
from app.database.base import Base
from app.database.mixins import TimestampMixin


class PendingTreatment(Base, TimestampMixin):
    """
    Bridges visits for multi-session treatments (RCT, ortho, implant).
    Created automatically when a branch_status=planned or RCT Multi Session is confirmed.
    One pending created at a time — next one created only when current session finalizes.

    status: pending | scheduled | completed | abandoned
    """

    __tablename__ = "pending_treatments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="RESTRICT"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False)
    case_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("consultation_cases.id", ondelete="SET NULL"), nullable=True)
    # Where this was planned — the branch that created this pending treatment
    origin_branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("consultation_branches.id", ondelete="RESTRICT"), nullable=False)

    # What needs to be done — mirrors branch procedure fields
    procedure_category: Mapped[str] = mapped_column(String(50), nullable=False)
    procedure_name: Mapped[str] = mapped_column(String(100), nullable=False)
    procedure_detail: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tooth_ids: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    # pending | scheduled | completed | abandoned

    # Set when receptionist books appointment for this pending treatment
    scheduled_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    # Set when treatment is completed — links back to the visit that did it
    completed_in_visit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("consultation_visits.id", ondelete="SET NULL"),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Session context — for RCT, ortho, implant
    # Stored flat for fast querying (also in meta on branch, but here for direct access)
    session_number: Mapped[int | None] = mapped_column(String(10), nullable=True)
    session_total: Mapped[int | None] = mapped_column(String(10), nullable=True)

    # Relationships
    origin_branch: Mapped["ConsultationBranch"] = relationship(
        "ConsultationBranch",
        foreign_keys=[origin_branch_id],
    )

    __table_args__ = (
        Index("idx_pending_patient", "patient_id", "clinic_id", "status"),
        Index("idx_pending_clinic_status", "clinic_id", "status"),
        Index("idx_pending_origin", "origin_branch_id"),
        Index("idx_pending_scheduled", "clinic_id", "scheduled_date"),
    )

    def __repr__(self) -> str:
        return f"<PendingTreatment id={self.id} proc={self.procedure_name} status={self.status}>"
