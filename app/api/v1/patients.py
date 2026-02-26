# Standard library
import uuid

# Third-party
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

# Internal — dependencies
from app.dependencies import DbSession
from app.rbac.dependencies import AuthenticatedUser, require_permission
from app.rbac.permissions import PATIENT_READ, PATIENT_WRITE

# Internal — schemas + service
from app.schemas.patient import PatientCreate, PatientListItem, PatientResponse, PatientUpdate
from app.schemas.common import PaginatedMeta, PaginatedResponse, SuccessResponse
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.post(
    "",
    response_model=SuccessResponse[PatientResponse],
    status_code=201,
    dependencies=[Depends(require_permission(PATIENT_WRITE))],
)
async def create_patient(
    body: PatientCreate,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Create a new patient. Auto-generates PAT-YYYY-NNNNN code."""
    service = PatientService(db)
    result = await service.create_patient(body, current_user.clinic_id)
    return JSONResponse(
        status_code=201,
        content={
            "success": True,
            "message": "Patient created successfully",
            "data": result.model_dump(mode="json"),
        },
    )


@router.get(
    "",
    response_model=PaginatedResponse[PatientListItem],
    dependencies=[Depends(require_permission(PATIENT_READ))],
)
async def list_patients(
    current_user: AuthenticatedUser,
    db: DbSession,
    search: str | None = Query(None, description="Search by name, phone, or patient code"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> JSONResponse:
    """List patients with optional search and pagination."""
    service = PatientService(db)
    result = await service.list_patients(
        current_user.clinic_id, search=search, page=page, per_page=per_page
    )
    return JSONResponse(content={
        "success": True,
        "message": "Patients retrieved",
        "data": [item.model_dump(mode="json") for item in result.items],
        "meta": result.to_meta(),
    })


@router.get(
    "/{patient_id}",
    response_model=SuccessResponse[PatientResponse],
    dependencies=[Depends(require_permission(PATIENT_READ))],
)
async def get_patient(
    patient_id: uuid.UUID,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Get a single patient by ID."""
    service = PatientService(db)
    result = await service.get_patient(patient_id, current_user.clinic_id)
    return JSONResponse(content={
        "success": True,
        "message": "Patient retrieved",
        "data": result.model_dump(mode="json"),
    })


@router.patch(
    "/{patient_id}",
    response_model=SuccessResponse[PatientResponse],
    dependencies=[Depends(require_permission(PATIENT_WRITE))],
)
async def update_patient(
    patient_id: uuid.UUID,
    body: PatientUpdate,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Partial update — only provided fields are changed."""
    service = PatientService(db)
    result = await service.update_patient(patient_id, current_user.clinic_id, body)
    return JSONResponse(content={
        "success": True,
        "message": "Patient updated",
        "data": result.model_dump(mode="json"),
    })


# ============================================================
# Patient sub-routes (added in Phase 7)
# ============================================================

@router.get(
    "/{patient_id}/appointments",
    response_model=PaginatedResponse,
    dependencies=[Depends(require_permission(PATIENT_READ))],
)
async def get_patient_appointments(
    patient_id: uuid.UUID,
    current_user: AuthenticatedUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> JSONResponse:
    """List all appointments for a specific patient (paginated)."""
    from app.services.appointment_service import AppointmentService
    service = AppointmentService(db)
    result = await service.get_patient_appointments(
        patient_id, current_user.clinic_id, page=page, per_page=per_page
    )
    return JSONResponse(content={
        "success": True,
        "message": "Patient appointments retrieved",
        "data": [item.model_dump(mode="json") for item in result.items],
        "meta": result.to_meta(),
    })



