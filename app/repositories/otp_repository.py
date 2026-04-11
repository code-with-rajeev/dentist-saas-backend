#Standard library
import uuid
from datetime import datetime, timezone

#Third-party
from sqlalchemy import delete, select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

#Internal
from app.models.user_otp import UserOtp

class OtpRepository:
    """Data access layer for user OTPs."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # Fetch OTP by email and purpose. No validity filtering here — the service layer will handle that.
    async def get_by_email_and_purpose(
        self, email: str, purpose: str
    ) -> UserOtp | None:
        result = await self.db.execute(
            select(UserOtp).where(
                UserOtp.email == email,
                UserOtp.purpose == purpose,
            )
        )
        return result.scalar_one_or_none()
    
    # Delete any existing OTP for this email+purpose, then insert fresh.
    async def replace_otp(
        self,
        user_id: uuid.UUID,
        email: str,
        otp_hash: str,
        purpose: str,
        expires_at: datetime,
        send_count: int,
        window_start: datetime,
        is_blocked: bool = False,
        blocked_until: datetime | None = None,
    ) -> UserOtp:
        await self.db.execute(
            delete(UserOtp).where(
                UserOtp.email == email,
                UserOtp.purpose == purpose,
            )
        )
        otp_record = UserOtp(
            user_id=user_id,
            email=email,
            otp_hash=otp_hash,
            purpose=purpose,
            expires_at=expires_at,
            otp_send_count=send_count,
            otp_attempt_count=0,
            window_start=window_start,
            is_blocked=is_blocked,
            blocked_until=blocked_until,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(otp_record)
        await self.db.flush()
        return otp_record

    # Called on every wrong OTP guess. Service decides when to block.
    async def increment_attempt_count(self, otp_id: uuid.UUID) -> None:
        await self.db.execute(
            update(UserOtp)
            .where(UserOtp.id == otp_id)
            .values(otp_attempt_count=UserOtp.otp_attempt_count + 1)
        )
        await self.db.flush()

    # Hard block this email+purpose after too many wrong attempts.
    async def set_blocked(
        self, otp_id: uuid.UUID, blocked_until: datetime
    ) -> None:
        await self.db.execute(
            update(UserOtp)
            .where(UserOtp.id == otp_id)
            .values(is_blocked=True, blocked_until=blocked_until)
        )
        await self.db.flush()

    # Called on successful verification — row is gone, OTP cannot be replayed.
    async def delete_otp(self, otp_id: uuid.UUID) -> None:
        await self.db.execute(
            delete(UserOtp).where(UserOtp.id == otp_id)
        )
        await self.db.flush()

    # Mark OTP as used. Row stays to preserve rate limit window.
    async def consume_otp(self, otp_id: uuid.UUID, window_start: datetime, send_count: int) -> None:
        await self.db.execute(
            update(UserOtp)
            .where(UserOtp.id == otp_id)
            .values(
                otp_hash   = "",          # hash is gone — cannot be verified again
                otp_attempt_count = 0,    # reset attempts
                window_start = window_start, # keep the same window start for rate limiting
                otp_send_count = send_count+1, # increment send count for the next OTP in the same window
                expires_at = datetime.now(timezone.utc),  # expired immediately
                blocked_until = None,
                is_blocked = False,
            )
        )
        await self.db.flush()