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
from app.schemas.consultation_visit import (
    BranchCreate,
    BranchUpdate,
    VisitCreate,
    VisitListItem,
    VisitResponse,
    VisitUpdate,
    PendingTreatmentResponse,
)
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.services.consultation_service import ConsultationService

router = APIRouter(prefix="/consultations", tags=["Consultations"])

# ============================================================
# Pending treatments
# ============================================================

@router.get(
    "/pending-treatments",
    response_model=SuccessResponse[list[PendingTreatmentResponse]],
    dependencies=[Depends(require_permission(PATIENT_READ))],
)
async def get_patient_pending_treatments(
    current_user: AuthenticatedUser,
    db: DbSession,
    patient_id: uuid.UUID = Query(..., description="Patient ID"),
) -> JSONResponse:
    """List all pending treatments for a patient. Used to pre-fill returning patient flow."""
    svc = ConsultationService(db)
    result = await svc.get_patient_pending_treatments(patient_id, current_user.clinic_id)
    return JSONResponse(content={"success": True, "message": "Pending treatments retrieved", "data": [r.model_dump(mode="json") for r in result]})


# ============================================================
# Collection routes
# ============================================================

@router.post(
    "",
    response_model=SuccessResponse[VisitResponse],
    status_code=201,
    dependencies=[Depends(require_permission(CONSULTATION_WRITE)), Depends(require_owner())],
)
async def create_visit(
    body: VisitCreate,
    current_user: AuthenticatedUser,
    db: DbSession,
    patient_id: uuid.UUID = Query(..., description="Patient ID"),
) -> JSONResponse:
    """Create a draft visit for a waiting appointment. Owner only."""
    svc = ConsultationService(db)
    result = await svc.create_visit(body, patient_id, current_user.clinic_id, current_user)
    return JSONResponse(status_code=201, content={"success": True, "message": "Visit created", "data": result.model_dump(mode="json")})


@router.patch(
    "/{visit_id}",
    response_model=SuccessResponse[VisitResponse],
    dependencies=[Depends(require_permission(CONSULTATION_WRITE)), Depends(require_owner())],
)
async def update_visit(
    visit_id: uuid.UUID,
    body: VisitUpdate,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Update visit-level fields (follow-up, total_paid). Rejected if finalized."""
    svc = ConsultationService(db)
    result = await svc.update_visit(visit_id, current_user.clinic_id, body)
    return JSONResponse(content={"success": True, "message": "Visit updated", "data": result.model_dump(mode="json")})


@router.post(
    "/{visit_id}/finalize",
    response_model=SuccessResponse[VisitResponse],
    dependencies=[Depends(require_permission(CONSULTATION_SUBMIT)), Depends(require_owner())],
)
async def finalize_visit(
    visit_id: uuid.UUID,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """
    Lock visit + auto-complete appointment + auto-create pending treatments for planned branches.
    Owner only. Requires at least one branch.
    """
    svc = ConsultationService(db)
    result = await svc.finalize_visit(visit_id, current_user.clinic_id)
    return JSONResponse(content={"success": True, "message": "Visit finalized and locked", "data": result.model_dump(mode="json")})


@router.get(
    "/{visit_id}",
    response_model=SuccessResponse[VisitResponse],
    dependencies=[Depends(require_permission(PATIENT_READ))],
)
async def get_visit(
    visit_id: uuid.UUID,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Get full visit with all branches and medications."""
    svc = ConsultationService(db)
    result = await svc.get_visit(visit_id, current_user.clinic_id)
    return JSONResponse(content={"success": True, "message": "Visit retrieved", "data": result.model_dump(mode="json")})


@router.get(
    "",
    response_model=PaginatedResponse,
    dependencies=[Depends(require_permission(PATIENT_READ))],
)
async def list_patient_visits(
    current_user: AuthenticatedUser,
    db: DbSession,
    patient_id: uuid.UUID = Query(..., description="Patient ID"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> JSONResponse:
    """List all visits for a patient — lean shape."""
    svc = ConsultationService(db)
    result = await svc.get_patient_visits(patient_id, current_user.clinic_id, page=page, per_page=per_page)
    return JSONResponse(content={
        "success": True,
        "message": "Visits retrieved",
        "data": [item.model_dump(mode="json") for item in result.items],
        "meta": result.to_meta(),
    })


# ============================================================
# Branch routes
# ============================================================

@router.post(
    "/{visit_id}/branches",
    response_model=SuccessResponse[dict],
    status_code=201,
    dependencies=[Depends(require_permission(CONSULTATION_WRITE)), Depends(require_owner())],
)
async def add_branch(
    visit_id: uuid.UUID,
    body: BranchCreate,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """
    Add a new branch (case) to a draft visit.
    Each branch = one complaint / procedure / billing unit.
    Multiple branches allowed per visit.
    """
    svc = ConsultationService(db)
    result = await svc.add_branch(visit_id, current_user.clinic_id, body)
    return JSONResponse(status_code=201, content={"success": True, "message": "Branch added", "data": result.model_dump(mode="json")})


@router.patch(
    "/{visit_id}/branches/{branch_id}",
    response_model=SuccessResponse[dict],
    dependencies=[Depends(require_permission(CONSULTATION_WRITE)), Depends(require_owner())],
)
async def update_branch(
    visit_id: uuid.UUID,
    branch_id: uuid.UUID,
    body: BranchUpdate,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Update a branch. Rejected if parent visit is finalized."""
    svc = ConsultationService(db)
    result = await svc.update_branch(visit_id, branch_id, current_user.clinic_id, body)
    return JSONResponse(content={"success": True, "message": "Branch updated", "data": result.model_dump(mode="json")})


# ============================================================
# PDF routes
# ============================================================

@router.post(
    "/{visit_id}/generate-report",
    response_model=SuccessResponse[VisitResponse],
    dependencies=[Depends(require_permission(CONSULTATION_WRITE)), Depends(require_owner())],
)
async def generate_pdf_report(
    visit_id: uuid.UUID,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Generate PDF for a finalized visit. Owner only."""
    svc = ConsultationService(db)
    result = await svc.generate_pdf_report(visit_id, current_user.clinic_id)
    return JSONResponse(content={"success": True, "message": "PDF report generated", "data": result.model_dump(mode="json")})


@router.get(
    "/{visit_id}/report",
    dependencies=[Depends(require_permission(PATIENT_READ))],
)
async def download_pdf_report(
    visit_id: uuid.UUID,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> FileResponse:
    """Download PDF binary. 400 if not finalized, 404 if not generated."""
    svc = ConsultationService(db)
    file_path = await svc.get_pdf_path(visit_id, current_user.clinic_id)
    return FileResponse(path=file_path, media_type="application/pdf", filename=f"visit_{visit_id}.pdf")


# ============================================================
# Stubs (Post-MVP)
# ============================================================

@router.post("/{visit_id}/send-report")
async def send_report_whatsapp(visit_id: uuid.UUID, current_user: AuthenticatedUser) -> dict:
    """STUB: WhatsApp send not active in MVP."""
    return {"success": True, "message": "STUB: WhatsApp send not active in MVP"}
