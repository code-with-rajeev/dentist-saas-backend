# Standard library
import uuid
from datetime import datetime, timedelta, timezone
#import asyncio
# Third-party
from sqlalchemy.ext.asyncio import AsyncSession  
from fastapi.concurrency import run_in_threadpool

# Internal — core
from app.core.exceptions import (
    RateLimitException,
    ValidationException,
    NotFoundException,
    AuthException,
)
from app.constants.messages import (
    OTP_EXPIRED,
    OTP_INVALID,
    OTP_RATE_LIMITED,
    OTP_BLOCKED,
    USER_NOT_FOUND,
    RESET_TOKEN_INVALID,
)
from app.constants.messages import OtpPurpose
from app.core.security import create_access_token, decode_token, hash_password

# Internal — repositories
from app.repositories.otp_repository import OtpRepository
from app.repositories.user_repository import UserRepository

# Internal — utils
from app.utils.otp_utils import generate_otp, hash_otp, verify_otp, otp_expiry

# Internal — services
from app.services.email_service import EmailService


# Rate limit config
WINDOW_SECONDS      = 600   # 10 minutes
MAX_SENDS           = 3     # OTP emails per window
MAX_ATTEMPTS        = 5     # wrong guesses per email before hard block
BLOCK_SECONDS       = 86400 # 24 hour hard block


class OtpService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.otp_repo   = OtpRepository(db)
        self.user_repo  = UserRepository(db)
        self.email_svc  = EmailService()
        #self.email_semaphore = asyncio.Semaphore(3) # limit to 3 concurrent emails, NOT WORTH AT THIS SCALE

    async def send_otp(
        self, email: str, purpose: OtpPurpose
    ) -> None:
        """
        Issue a new OTP for the given email+purpose.
        Enforces send-rate limiting with fixed time window.
        """
        now = datetime.now(timezone.utc)

        # Verify user exists before doing anything else
        user = await self.user_repo.get_by_email(email)
        if not user:
            # Don't reveal whether email exists — silent return
            # This prevents email enumeration attacks
            return

        existing = await self.otp_repo.get_by_email_and_purpose(email, purpose)

        if existing:
            # Hard block check
            if existing.is_blocked:
                if existing.blocked_until and existing.blocked_until > now:
                    raise RateLimitException(
                        code=OTP_BLOCKED,
                        message="Too many attempts. Try again after 24 hours.",
                    )
                # Block expired — fall through, treat as fresh window

            # Window check — has the 10-minute window expired?
            window_elapsed = (now - existing.window_start).total_seconds()

            if window_elapsed > WINDOW_SECONDS:
                # Window expired — reset
                current_count = 0
                window_start  = now
            else:
                current_count = existing.otp_send_count
                window_start  = existing.window_start  # preserve original window start

            if current_count >= MAX_SENDS:
                raise RateLimitException(
                    code=OTP_RATE_LIMITED,
                    message=f"Too many OTP requests. Try again in {int((WINDOW_SECONDS - window_elapsed) // 60) + 1} minutes.",
                )
        else:
            # No existing row — fresh start
            current_count = 0
            window_start  = now

        # All checks passed — generate and store
        otp_plain  = generate_otp()
        otp_hashed = hash_otp(otp_plain)

        await self.otp_repo.replace_otp(
            user_id      = user.id,
            email        = email,
            otp_hash     = otp_hashed,
            purpose      = purpose,
            expires_at   = otp_expiry(),
            send_count   = current_count + 1,
            window_start = window_start,
            is_blocked   = False,
            blocked_until= None,
        )
        await self.db.commit()

        await run_in_threadpool(
                self.email_svc.send_otp_email,
                email     = email,
                otp       = otp_plain,
                purpose   = purpose,
        )

    async def verify_otp_and_issue_token(
        self, email: str, purpose: OtpPurpose, otp_plain: str
    ) -> str:
        """
        Verify OTP for email+purpose.
        On success: deletes the row (no replay possible).
        On failure: increments attempt count, blocks after MAX_ATTEMPTS.
        """
        now = datetime.now(timezone.utc)

        otp_record = await self.otp_repo.get_by_email_and_purpose(email, purpose)

        if not otp_record:
            raise ValidationException(code=OTP_INVALID, message="Invalid or expired OTP.")

        # Block check
        if otp_record.is_blocked:
            raise RateLimitException(
                code=OTP_BLOCKED,
                message="Too many incorrect attempts. Try again after 24 hours.",
            )

        # Expiry check
        if otp_record.expires_at < now:
            raise ValidationException(code=OTP_EXPIRED, message="OTP has expired. Request a new one.")

        # Wrong OTP
        if not verify_otp(otp_plain, otp_record.otp_hash):
            new_attempt_count = otp_record.otp_attempt_count + 1
            await self.otp_repo.increment_attempt_count(otp_record.id)
            await self.db.commit()
            if new_attempt_count >= MAX_ATTEMPTS:
                await self.otp_repo.set_blocked(
                    otp_id       = otp_record.id,
                    blocked_until= now + timedelta(seconds=BLOCK_SECONDS),
                )
                await self.db.commit()
                raise RateLimitException(
                    code=OTP_BLOCKED,
                    message="Too many incorrect attempts. Try again after 24 hours.",
                )

            raise ValidationException(
                code=OTP_INVALID,
                message=f"Incorrect OTP. {MAX_ATTEMPTS - new_attempt_count} attempts remaining.",
            )
        # Consume the OTP & increase send count, while keeping the record for audit/history. This also prevents replay attacks.
        await self.otp_repo.consume_otp(otp_record.id, otp_record.window_start, otp_record.otp_send_count)

        # issue short-lived access token for password reset flow
        reset_token = create_access_token(
            data = {"sub": str(otp_record.user_id), "purpose": purpose.value},
        )
        return reset_token
    
    async def reset_password(self, reset_token: str, new_password: str) -> None:
        """
        Reset user's password. This is called after OTP verification in the password reset flow.
        """
        try:
            payload = decode_token(reset_token)
        except Exception:
            raise AuthException(code=RESET_TOKEN_INVALID, message="Invalid reset token")

        if payload.get("purpose") != OtpPurpose.PASSWORD_RESET.value:
            raise AuthException(code=RESET_TOKEN_INVALID, message="Invalid token purpose")

        user_id = payload.get("sub")
        hashed = hash_password(new_password)
        await self.user_repo.update_password(uuid.UUID(user_id), hashed)
