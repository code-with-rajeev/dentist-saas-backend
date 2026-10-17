# Standard library
import uuid

# Third-party
from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Internal
from app.database.base import Base
from app.database.mixins import TimestampMixin


class ConsultationBranch(Base, TimestampMixin):
    """
    One branch = one clinical case within a visit.
    A visit can have multiple branches (e.g. tooth pain + cleaning same day).
    Each branch owns its own medications, procedure, diagnosis, and billing.

    entry_point   → which flow was used (new_pain, cleaning, cosmetic, ortho, returning, custom)
    branch_status → done | planned | deferred | referred
    payment_status→ unpaid | paid | waived

    L1 = procedure_category  (Endodontic, Restorative, Surgical...)
    L2 = procedure_name      (RCT, Filling, Extraction...)
    L3 = procedure_detail    (Single Visit, Multi Session, Simple...)

    meta JSONB absorbs all clinic-customizable fields:
        session_number, session_total  → RCT / ortho / implant session tracking
        progress_upper, progress_lower → ortho arch progress
        photos                         → cosmetic before/after URLs
        referral_to                    → referred branches
        investigation_requested        → OPG, CBCT etc.
        custom fields dentist defines  → braces_type, material, shade etc.
    """

    __tablename__ = "consultation_branches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="RESTRICT"), nullable=False)
    visit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("consultation_visits.id", ondelete="CASCADE"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False)
    case_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("consultation_cases.id", ondelete="SET NULL"), nullable=True)
    # Entry point
    entry_point: Mapped[str] = mapped_column(String(30), nullable=False)
    # new_pain | cleaning | cosmetic | ortho | returning | custom

    # Diagnosis engine output — null for non-diagnostic branches
    presenting_problem: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # tooth_pain | gum | mouth_ulcer | jaw_pain | swelling | post_extraction

    diagnosis: Mapped[str | None] = mapped_column(String(200), nullable=True)
    diagnosis_custom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Procedure engine output — L1 → L2 → L3
    procedure_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    procedure_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    procedure_detail: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Tooth selection — FDI numbers or area labels
    tooth_ids: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # e.g. ["26"] or ["Full mouth"] or ["11", "12"]

    # Clinical notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Branch outcome
    branch_status: Mapped[str] = mapped_column(String(20), nullable=False, default="done", server_default="done")
    # done | planned | deferred | referred

    # Billing
    billing_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.00, server_default="0.00")
    payment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unpaid", server_default="unpaid")
    # unpaid | paid | waived

    # Flexible meta — session tracking, ortho progress, photos, custom fields
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    visit: Mapped["ConsultationVisit"] = relationship(
        "ConsultationVisit",
        back_populates="branches",
        foreign_keys=[visit_id],
    )
    medications: Mapped[list["Medication"]] = relationship(
        "Medication",
        back_populates="branch",
        cascade="all, delete-orphan",
        order_by="Medication.sort_order",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_branch_visit", "visit_id"),
        Index("idx_branch_patient", "patient_id", "clinic_id"),
        Index("idx_branch_status", "clinic_id", "branch_status", "payment_status"),
        Index("idx_branch_entry", "clinic_id", "entry_point"),
        Index("idx_branch_diagnosis", "clinic_id", "diagnosis"),
    )

    def __repr__(self) -> str:
        return f"<ConsultationBranch id={self.id} entry={self.entry_point} status={self.branch_status}>"
