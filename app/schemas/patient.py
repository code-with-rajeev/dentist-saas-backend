# Standard library
import uuid
from datetime import date, datetime

# Third-party
from pydantic import BaseModel, EmailStr, Field


# ============================================================
# Request schemas
# ============================================================

class PatientCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=120)
    age: int = Field(..., ge=1, le=120)
    gender: str | None = Field(None, pattern="^(male|female|other)$")
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    general_notes: str | None = None


class PatientUpdate(BaseModel):
    """All fields optional — partial update only."""
    full_name: str | None = Field(None, min_length=1, max_length=120)
    age: int | None = Field(None, ge=1, le=120)
    gender: str | None = Field(None, pattern="^(male|female|other)$")
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    general_notes: str | None = None


# ============================================================
# Response schemas
# ============================================================

class PatientResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    patient_code: str
    full_name: str
    age: int
    gender: str | None
    phone: str | None
    email: str | None
    general_notes: str | None
    total_appointments: int = 0
    last_visit: date | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PatientListItem(BaseModel):
    """Lean shape for list/search results (no heavy fields)."""
    id: uuid.UUID
    patient_code: str
    full_name: str
    age: int
    phone: str | None
    total_appointments: int = 0
    last_visit: date | None = None

    model_config = {"from_attributes": True}
