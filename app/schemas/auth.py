# Standard library
import uuid
from datetime import datetime
from app.constants.messages import OtpPurpose

# Third-party
from pydantic import BaseModel, EmailStr, Field, field_validator


# ============================================================
# Request schemas
# ============================================================

class RegisterRequest(BaseModel):
    clinic_name: str = Field(..., min_length=2, max_length=150)
    dentist_name: str = Field(..., min_length=2, max_length=120)
    dentist_reg_id: str | None = Field(None, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    phone: str | None = Field(None, max_length=20)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ============================================================
# Response schemas
# ============================================================

class ClinicResponse(BaseModel):
    id: uuid.UUID
    name: str
    dentist_name: str
    status: str

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    clinic_id: uuid.UUID
    permissions: list[str]
    is_active: bool

    model_config = {"from_attributes": True}


class RegisterResponse(BaseModel):
    user: UserResponse
    clinic: ClinicResponse
    access_token: str
    token_type: str = "bearer"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: EmailStr
    role: str
    clinic_id: uuid.UUID
    clinic_name: str
    permissions: list[str]
    is_active: bool
    last_login_at: datetime | None

    model_config = {"from_attributes": True}

class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    purpose: OtpPurpose

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)
    purpose: OtpPurpose

class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=8)