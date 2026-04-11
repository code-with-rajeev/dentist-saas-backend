import random
import string
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from app.constants.values import OTP_EXPIRE_MINUTES, OTP_LENGTH

otp_context = CryptContext(schemes=["bcrypt"], deprecated="auto")




def generate_otp() -> str:
    """Generate a random numeric OTP of specified length."""
    return "".join(random.choices(string.digits, k=OTP_LENGTH))


def hash_otp(plain_otp: str) -> str:
    """Hash the plain OTP using bcrypt."""
    return otp_context.hash(plain_otp)


def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    """Verify the plain OTP against the hashed OTP."""
    return otp_context.verify(plain_otp, hashed_otp)


def otp_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)