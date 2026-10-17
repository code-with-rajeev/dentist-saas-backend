# Standard library
import uuid
from datetime import datetime
from decimal import Decimal

# Third-party
from pydantic import BaseModel, Field

from app.constants.consultation import BranchStatus, EntryPoint, PaymentStatus, PresentingProblem


# ============================================================
# Medication schemas — unchanged shape, reused across branch
# ============================================================

class MedicationCreate(BaseModel):
    med_library_id: uuid.UUID | None = None
    name: str = Field(..., min_length=1, max_length=200)
    dosage: str | None = Field(None, max_length=100)
    frequency: str | None = Field(None, max_length=100)
    duration: str | None = Field(None, max_length=100)
    instructions: str | None = Field(None, max_length=500)
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
# Branch schemas
# ============================================================

class BranchCreate(BaseModel):
    """Dentist submits one branch at a time during consultation flow."""
    entry_point: EntryPoint
    presenting_problem: PresentingProblem | None = None
    diagnosis: str | None = Field(None, max_length=200)
    diagnosis_custom: bool = False
    procedure_category: str | None = Field(None, max_length=50)
    procedure_name: str | None = Field(None, max_length=100)
    procedure_detail: str | None = Field(None, max_length=100)
    tooth_ids: list[str] | None = None
    notes: str | None = None
    case_id: uuid.UUID | None = None
    branch_status: BranchStatus = BranchStatus.DONE
    billing_amount: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    payment_status: PaymentStatus = PaymentStatus.UNPAID
    meta: dict | None = None
    medications: list[MedicationCreate] = Field(default_factory=list)


class BranchUpdate(BaseModel):
    """All fields optional — partial update. Locked after visit finalized."""
    presenting_problem: PresentingProblem | None = None
    diagnosis: str | None = Field(None, max_length=200)
    diagnosis_custom: bool | None = None
    procedure_category: str | None = Field(None, max_length=50)
    procedure_name: str | None = Field(None, max_length=100)
    procedure_detail: str | None = Field(None, max_length=100)
    tooth_ids: list[str] | None = None
    notes: str | None = None
    branch_status: BranchStatus | None = None
    billing_amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    payment_status: PaymentStatus | None = None
    meta: dict | None = None
    medications: list[MedicationCreate] | None = None
    # None = don't touch | [] = clear all


class BranchResponse(BaseModel):
    id: uuid.UUID
    visit_id: uuid.UUID
    entry_point: str
    presenting_problem: str | None
    diagnosis: str | None
    diagnosis_custom: bool
    procedure_category: str | None
    procedure_name: str | None
    procedure_detail: str | None
    tooth_ids: list[str] | None
    case_id: uuid.UUID | None = None
    notes: str | None
    branch_status: str
    billing_amount: Decimal
    payment_status: str
    meta: dict | None
    medications: list[MedicationResponse]
    created_at: datetime
    model_config = {"from_attributes": True}


# ============================================================
# Visit schemas
# ============================================================

class VisitCreate(BaseModel):
    """Create a draft visit. Branches added separately via POST /branches."""
    appointment_id: uuid.UUID
    # Follow-up — optional, set at any point before finalize
    is_follow_up_required: bool = False
    follow_up_notes: str | None = None
    follow_up_days: int | None = Field(None, ge=1, le=365)


class VisitUpdate(BaseModel):
    """Update visit-level fields only. Branch updates go to PATCH /branches/{id}."""
    is_follow_up_required: bool | None = None
    follow_up_notes: str | None = None
    follow_up_days: int | None = Field(None, ge=1, le=365)
    total_paid: Decimal | None = Field(None, ge=0, decimal_places=2)


class VisitResponse(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    appointment_id: uuid.UUID
    patient_id: uuid.UUID
    dentist_id: uuid.UUID
    is_finalized: bool
    finalized_at: datetime | None
    total_billed: Decimal
    total_paid: Decimal
    is_follow_up_required: bool
    follow_up_notes: str | None
    follow_up_days: int | None
    report_generated: bool
    report_path: str | None
    report_generated_at: datetime | None
    branches: list[BranchResponse]
    created_at: datetime
    model_config = {"from_attributes": True}


class VisitListItem(BaseModel):
    """Lean shape for patient visit history list."""
    id: uuid.UUID
    appointment_id: uuid.UUID
    total_billed: Decimal
    total_paid: Decimal
    is_finalized: bool
    finalized_at: datetime | None
    branch_count: int
    is_follow_up_required: bool
    report_generated: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ============================================================
# Pending treatment schemas
# ============================================================

class PendingTreatmentResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    origin_branch_id: uuid.UUID
    procedure_category: str
    procedure_name: str
    procedure_detail: str | None
    tooth_ids: list[str] | None
    case_id: uuid.UUID | None
    status: str
    scheduled_date: str | None
    session_number: str | None
    session_total: str | None
    notes: str | None
    created_at: datetime
    model_config = {"from_attributes": True}
