# Standard library
import uuid
from datetime import date, datetime
from typing import Literal

# Third-party
from pydantic import BaseModel, Field


# ============================================================
# Request schemas
# ============================================================

class AppointmentCreate(BaseModel):
    patient_id: uuid.UUID
    appointment_type: str = Field(default="regular", pattern="^(regular|follow_up|walk_in)$")
    scheduled_date: date
    scheduled_time_slot: str | None = Field(None, max_length=20)   # e.g. "10:00", "10:00-10:30"
    notes: str | None = None
    parent_appointment_id: uuid.UUID | None = None   # required when appointment_type=follow_up


class AppointmentCancelRequest(BaseModel):
    reason: str | None = Field(None, max_length=500)


class AppointmentRescheduleRequest(BaseModel):
    scheduled_date: date
    scheduled_time_slot: str | None = Field(None, max_length=20)


class AppointmentFilter(BaseModel):
    """Query params for list endpoint."""
    status: str | None = None
    appt_date: date | None = Field(None, alias="date")
    date_from: date | None = None
    date_to: date | None = None
    patient_id: uuid.UUID | None = None
    appointment_type: str | None = None
    search: str | None = None     # search by appointment_code

    model_config = {"populate_by_name": True}


# ============================================================
# Response schemas
# ============================================================

class PatientSummary(BaseModel):
    id: uuid.UUID
    full_name: str
    patient_code: str
    phone: str | None

    model_config = {"from_attributes": True}


class AppointmentResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    appointment_code: str
    appointment_type: str
    status: str
    queue_position: int | None
    scheduled_date: date
    scheduled_time_slot: str | None
    notes: str | None
    cancelled_reason: str | None
    cancelled_at: datetime | None
    confirmed_at: datetime | None
    patient_id: uuid.UUID
    parent_appointment_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AppointmentListItem(BaseModel):
    """Lean shape for list."""
    id: uuid.UUID
    appointment_code: str
    appointment_type: str
    status: str
    queue_position: int | None
    scheduled_date: date
    scheduled_time_slot: str | None
    patient_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class QueueItem(BaseModel):
    id: uuid.UUID
    appointment_code: str
    queue_position: int | None
    scheduled_time_slot: str | None
    patient_id: uuid.UUID

    model_config = {"from_attributes": True}


class QueueResponse(BaseModel):
    date: date
    total_waiting: int
    items: list[QueueItem]
