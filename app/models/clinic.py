# Standard library
import uuid

# Third-party
from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

# Internal
from app.database.base import Base
from app.database.mixins import TimestampMixin


class Clinic(Base, TimestampMixin):
    """
    One clinic = one SaaS tenant.
    Created automatically when a clinic owner registers.
    """

    __tablename__ = "clinics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ----------------------------------------------------------------
    # Identity fields — LOCKED after creation (enforced at app layer)
    # ----------------------------------------------------------------
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    gst_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    dentist_name: Mapped[str] = mapped_column(String(120), nullable=False)
    dentist_reg_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ----------------------------------------------------------------
    # Contact fields — EDITABLE via settings
    # ----------------------------------------------------------------
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # ----------------------------------------------------------------
    # Location — POST-MVP (maps/directions feature)
    # ----------------------------------------------------------------
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)

    # ----------------------------------------------------------------
    # Operating hours — EDITABLE
    # Format: {"monday": {"open": "09:00", "close": "18:00", "is_closed": false}, ...}
    # ----------------------------------------------------------------
    operating_hours: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # ----------------------------------------------------------------
    # Status
    # ----------------------------------------------------------------
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )

    # ----------------------------------------------------------------
    # Subscription — POST-MVP (columns exist now, unused in MVP)
    # ----------------------------------------------------------------
    subscription_plan: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default="free",
    )
    subscription_expires_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Locked fields — enforced at service layer (not DB)
    LOCKED_FIELDS = frozenset({"name", "gst_number", "dentist_name", "dentist_reg_id"})

    def __repr__(self) -> str:
        return f"<Clinic id={self.id} name={self.name}>"
