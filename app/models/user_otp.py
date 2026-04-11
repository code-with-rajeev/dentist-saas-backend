import uuid
from datetime import datetime, timezone
from sqlalchemy import UUID, VARCHAR, ForeignKey, TIMESTAMP, SmallInteger, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class UserOtp(Base):
    __tablename__ = "user_otps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(VARCHAR(150), nullable=False)
    otp_hash: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    purpose: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    # Rate limiting fields
    otp_send_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )
    otp_attempt_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )
    window_start: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    is_blocked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    blocked_until: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("uq_user_otp_email_purpose", "email", "purpose", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<UserOtp email={self.email} purpose={self.purpose} "
            f"blocked={self.is_blocked} send_count={self.otp_send_count}>"
        )