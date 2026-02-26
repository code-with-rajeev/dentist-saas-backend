# Standard library
import uuid
from datetime import datetime

# Third-party
from pydantic import BaseModel, EmailStr, Field, field_validator

# Internal
from app.rbac.permissions import ALL_PERMISSIONS, GRANTABLE_PERMISSIONS


# ============================================================
# Clinic Settings
# ============================================================

class OperatingHoursDay(BaseModel):
    open: str | None = None       # "09:00" format (HH:MM)
    close: str | None = None      # "18:00" format (HH:MM)
    is_closed: bool = False

    @field_validator("open", "close", mode="before")
    @classmethod
    def validate_time_format(cls, v):
        if v is None:
            return v
        parts = str(v).split(":")
        if len(parts) != 2:
            raise ValueError("Time must be in HH:MM format")
        h, m = parts
        if not (h.isdigit() and m.isdigit() and 0 <= int(h) <= 23 and 0 <= int(m) <= 59):
            raise ValueError("Time must be a valid HH:MM value (00:00–23:59)")
        return v


class ClinicSettingsResponse(BaseModel):
    id: uuid.UUID
    name: str
    gst_number: str | None
    dentist_name: str
    dentist_reg_id: str | None
    phone: str | None
    email: str | None
    address: str | None
    city: str | None
    state: str | None
    pincode: str | None
    operating_hours: dict
    status: str
    subscription_plan: str | None
    locked_fields: list[str]   # communicated to frontend so it can disable those inputs

    model_config = {"from_attributes": True}


class ClinicSettingsUpdate(BaseModel):
    """Only editable fields — locked fields excluded."""
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    address: str | None = None
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    pincode: str | None = Field(None, max_length=10)
    operating_hours: dict[str, OperatingHoursDay] | None = None


# ============================================================
# Staff Management
# ============================================================

class StaffCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="assistant")
    phone: str | None = Field(None, max_length=20)
    permissions: list[str] = Field(default_factory=list)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        from app.constants.roles import MemberRole
        valid = [r.value for r in MemberRole if r.value != "clinic_owner"]
        if v not in valid:
            raise ValueError(f"Role must be one of: {valid}")
        return v

    @field_validator("permissions", mode="before")
    @classmethod
    def validate_permissions(cls, v):
        invalid = [p for p in v if p not in ALL_PERMISSIONS]
        if invalid:
            raise ValueError(f"Invalid permission strings: {invalid}")
        owner_exclusive = [p for p in v if p not in GRANTABLE_PERMISSIONS]
        if owner_exclusive:
            raise ValueError(f"These permissions can only be held by clinic_owner: {owner_exclusive}")
        return v


class StaffPermissionsUpdate(BaseModel):
    permissions: list[str]

    @field_validator("permissions", mode="before")
    @classmethod
    def validate_permissions(cls, v):
        invalid = [p for p in v if p not in ALL_PERMISSIONS]
        if invalid:
            raise ValueError(f"Invalid permission strings: {invalid}")
        owner_exclusive = [p for p in v if p not in GRANTABLE_PERMISSIONS]
        if owner_exclusive:
            raise ValueError(f"These permissions can only be held by clinic_owner: {owner_exclusive}")
        return v


class PermissionResponse(BaseModel):
    id: uuid.UUID
    permission: str
    granted_at: datetime

    model_config = {"from_attributes": True}


class StaffResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    role: str
    phone: str | None
    is_active: bool
    permissions: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}
