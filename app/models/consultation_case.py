# Standard library
import uuid

# Third-party
from sqlalchemy import Date, ForeignKey, Integer, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Internal
from app.database.base import Base
from app.database.mixins import TimestampMixin

class ConsultationCase(Base, TimestampMixin):
    """
    Groups all branches across multiple visits
    that belong to one clinical problem.
    One RCT = one case. 4 sessions = 4 branches, all linked here.
    """
    __tablename__ = "consultation_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="RESTRICT"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False)
    origin_visit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("consultation_visits.id", ondelete="RESTRICT"), nullable=False)

    title: Mapped[str] = mapped_column(String(255))
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    procedure_category: Mapped[str] = mapped_column(String(100))
    procedure_name: Mapped[str] = mapped_column(String(100))
    tooth_ids: Mapped[list[str]] = mapped_column(JSONB)

    session_total: Mapped[int | None] = mapped_column(Integer, nullable=True)  # estimated e.g. 4
    sessions_completed: Mapped[int] = mapped_column(Integer, default=0)  # increments each visit, default 0

    status: Mapped[str] = mapped_column(String(20))  # active | completed | abandoned
    opened_date: Mapped[Date] = mapped_column(Date)
    closed_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    # Relationships