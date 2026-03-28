# Standard library
import uuid

# Third-party
from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

# Internal
from app.database.base import Base
from app.database.mixins import TimestampMixin


class MedLibrary(Base, TimestampMixin):
    """
    Master medication list shared across the system.

    source='system'  → preloaded Indian dental formulary, dentist_id=NULL
    source='custom'  → created by a specific dentist, dentist_id=set

    This is NOT the prescription record. That is models/medication.py.
    This is the library dentist searches and picks from.
    """

    __tablename__ = "med_library"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="custom"
        # values: 'system' | 'custom'
    )
    dentist_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        default=None,
        # NULL for system meds, dentist's clinic_member id for custom
    )
    usage_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    __table_args__ = (
        Index("idx_med_library_source", "source"),
        Index("idx_med_library_dentist", "dentist_id"),
        # No duplicate names per dentist per dosage — covers both system (dentist_id=NULL)
        # and custom (dentist_id=set)
        Index(
            "uq_med_library_name_dosage_dentist",
            "name", "dosage", "dentist_id",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<MedLibrary name={self.name} source={self.source}>"