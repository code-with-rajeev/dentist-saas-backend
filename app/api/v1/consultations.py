# Standard library
import uuid

# Third-party
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, JSONResponse

# Internal — dependencies
from app.dependencies import DbSession
from app.rbac.dependencies import AuthenticatedUser, require_owner, require_permission
from app.rbac.permissions import CONSULTATION_SUBMIT, CONSULTATION_WRITE, PATIENT_READ

# Internal — schemas + service
from app.schemas.consultation import (
    ConsultationCreate,
    ConsultationListItem,
    ConsultationResponse,
    ConsultationUpdate,
)
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.services.consultation_service import ConsultationService

router = APIRouter(prefix="/consultations", tags=["Consultations"])


@router.post(
    "",
    response_model=SuccessResponse[ConsultationResponse],
    status_code=201,
    dependencies=[
        Depends(require_permission(CONSULTATION_WRITE)),
        Depends(require_owner()),
    ],
)
async def create_consultation(
    body: ConsultationCreate,
    current_user: AuthenticatedUser,
    db: DbSession,
    patient_id: uuid.UUID = Query(..., description="Patient ID"),
) -> JSONResponse:
    """Create a draft consultation for a waiting appointment. Owner only."""
    service = ConsultationService(db)
    result = await service.create_consultation(body, patient_id, current_user.clinic_id, current_user)
    return JSONResponse(
        status_code=201,
        content={"success": True, "message": "Consultation created", "data": result.model_dump(mode="json")},
    )


@router.patch(
    "/{consultation_id}",
    response_model=SuccessResponse[ConsultationResponse],
    dependencies=[
        Depends(require_permission(CONSULTATION_WRITE)),
        Depends(require_owner()),
    ],
)
async def update_consultation(
    consultation_id: uuid.UUID,
    body: ConsultationUpdate,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Update a draft consultation. Rejected if already submitted (CONSULTATION_LOCKED). Owner only."""
    service = ConsultationService(db)
    result = await service.update_consultation(consultation_id, current_user.clinic_id, body)
    return JSONResponse(content={"success": True, "message": "Consultation updated", "data": result.model_dump(mode="json")})


@router.post(
    "/{consultation_id}/submit",
    response_model=SuccessResponse[ConsultationResponse],
    dependencies=[
        Depends(require_permission(CONSULTATION_SUBMIT)),
        Depends(require_owner()),
    ],
)
async def submit_consultation(
    consultation_id: uuid.UUID,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Lock form + auto-complete appointment. Owner only."""
    service = ConsultationService(db)
    result = await service.submit_consultation(consultation_id, current_user.clinic_id)
    return JSONResponse(content={"success": True, "message": "Consultation submitted and locked", "data": result.model_dump(mode="json")})


@router.get(
    "/{consultation_id}",
    response_model=SuccessResponse[ConsultationResponse],
    dependencies=[Depends(require_permission(PATIENT_READ))],
)
async def get_consultation(
    consultation_id: uuid.UUID,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Get full consultation detail including medications."""
    service = ConsultationService(db)
    result = await service.get_consultation(consultation_id, current_user.clinic_id)
    return JSONResponse(content={"success": True, "message": "Consultation retrieved", "data": result.model_dump(mode="json")})


@router.get(
    "",
    response_model=PaginatedResponse,
    dependencies=[Depends(require_permission(PATIENT_READ))],
)
async def list_patient_consultations(
    current_user: AuthenticatedUser,
    db: DbSession,
    patient_id: uuid.UUID = Query(..., description="Patient ID"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> JSONResponse:
    """List all consultations for a patient."""
    service = ConsultationService(db)
    result = await service.get_patient_consultations(
        patient_id, current_user.clinic_id, page=page, per_page=per_page
    )
    return JSONResponse(content={
        "success": True,
        "message": "Consultations retrieved",
        "data": [item.model_dump(mode="json") for item in result.items],
        "meta": result.to_meta(),
    })


@router.post(
    "/{consultation_id}/generate-report",
    response_model=SuccessResponse[ConsultationResponse],
    dependencies=[
        Depends(require_permission(CONSULTATION_WRITE)),
        Depends(require_owner()),
    ],
)
async def generate_pdf_report(
    consultation_id: uuid.UUID,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Generate + save PDF report for a submitted consultation. Owner only."""
    service = ConsultationService(db)
    result = await service.generate_pdf_report(consultation_id, current_user.clinic_id)
    return JSONResponse(content={"success": True, "message": "PDF report generated", "data": result.model_dump(mode="json")})


@router.get(
    "/{consultation_id}/report",
    dependencies=[Depends(require_permission(PATIENT_READ))],
)
async def download_pdf_report(
    consultation_id: uuid.UUID,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> FileResponse:
    """Download PDF binary. 400 if not submitted, 404 if not generated yet."""
    service = ConsultationService(db)
    file_path = await service.get_pdf_path(consultation_id, current_user.clinic_id)
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=f"consultation_{consultation_id}.pdf",
    )


# ============================================================
# Stub routes (Post-MVP)
# ============================================================

@router.post("/{consultation_id}/send-report")
async def send_report_whatsapp(
    consultation_id: uuid.UUID,
    current_user: AuthenticatedUser,
) -> dict:
    """STUB: WhatsApp send not active in MVP."""
    return {"success": True, "message": "STUB: WhatsApp send not active in MVP"}
