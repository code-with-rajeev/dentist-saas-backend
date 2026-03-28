# Standard library
import uuid
from datetime import datetime
from decimal import Decimal

# Third-party
from pydantic import BaseModel, Field


# ============================================================
# Medication schemas
# ============================================================

class MedicationCreate(BaseModel):
    med_library_id: uuid.UUID | None = None                  # optional link to master med library (NULL if dentist typed free-form med)
    name: str = Field(..., min_length=1, max_length=200)
    dosage: str | None = Field(None, max_length=100)         # e.g. "500mg"
    frequency: str | None = Field(None, max_length=100)      # e.g. "3 times a day"
    duration: str | None = Field(None, max_length=100)       # e.g. "5 days"
    instructions: str | None = Field(None, max_length=500)   # e.g. "After meals"
    sort_order: int = Field(default=0)


class MedicationResponse(BaseModel):
    id: uuid.UUID
    med_library_id: uuid.UUID | None
    name: str
    dosage: str | None
    frequency: str | None
    duration: str | None
    instructions: str | None
    sort_order: int

    model_config = {"from_attributes": True}


# ============================================================
# Consultation schemas
# ============================================================

class ConsultationCreate(BaseModel):
    appointment_id: uuid.UUID
    symptoms: str | None = None
    clinical_notes: str | None = None
    diagnosis: str | None = None
    fee_charged: Decimal | None = Field(None, ge=0, decimal_places=2)
    is_follow_up_required: bool = False
    follow_up_notes: str | None = None
    follow_up_days: int | None = Field(None, ge=1, le=365)
    medications: list[MedicationCreate] = Field(default_factory=list)


class ConsultationUpdate(BaseModel):
    """All fields optional — partial update. Medications list replaces entirely if provided."""
    symptoms: str | None = None
    clinical_notes: str | None = None
    diagnosis: str | None = None
    fee_charged: Decimal | None = Field(None, ge=0, decimal_places=2)
    is_follow_up_required: bool | None = None
    follow_up_notes: str | None = None
    follow_up_days: int | None = Field(None, ge=1, le=365)
    medications: list[MedicationCreate] | None = None   # None = don't touch; [] = clear all


class ConsultationResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    appointment_id: uuid.UUID
    patient_id: uuid.UUID
    dentist_id: uuid.UUID | None
    symptoms: str | None
    clinical_notes: str | None
    diagnosis: str | None
    fee_charged: Decimal | None
    is_follow_up_required: bool
    follow_up_notes: str | None
    follow_up_days: int | None
    medications: list[MedicationResponse]
    is_submitted: bool
    submitted_at: datetime | None
    report_generated: bool
    report_path: str | None
    report_generated_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConsultationListItem(BaseModel):
    """Lean shape for patient consultation history list."""
    id: uuid.UUID
    appointment_id: uuid.UUID
    fee_charged: Decimal | None
    diagnosis: str | None = None
    is_submitted: bool
    report_generated: bool
    is_follow_up_required: bool
    submitted_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
