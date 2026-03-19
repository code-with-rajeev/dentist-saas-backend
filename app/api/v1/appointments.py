# Standard library
import uuid
from datetime import date

# Third-party
from fastapi import APIRouter, Depends, Query, Body
from fastapi.responses import JSONResponse

# Internal — dependencies
from app.dependencies import DbSession
from app.rbac.dependencies import AuthenticatedUser, require_owner, require_permission
from app.rbac.permissions import (
    APPOINTMENT_CANCEL,
    APPOINTMENT_COMPLETE,
    APPOINTMENT_READ,
    APPOINTMENT_WRITE,
)

# Internal — schemas + service
from app.schemas.appointment import (
    AppointmentCancelRequest,
    AppointmentCreate,
    AppointmentFilter,
    AppointmentListItem,
    AppointmentRescheduleRequest,
    AppointmentResponse,
    QueueResponse,
)
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.services.appointment_service import AppointmentService

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post(
    "",
    response_model=SuccessResponse[AppointmentResponse],
    status_code=201,
    dependencies=[Depends(require_permission(APPOINTMENT_WRITE))],
)
async def create_appointment(
    body: AppointmentCreate, current_user: AuthenticatedUser, db: DbSession
) -> JSONResponse:
    """Create a new appointment in 'pending' status."""
    service = AppointmentService(db)
    result = await service.create_appointment(body, current_user.clinic_id, current_user)
    return JSONResponse(
        status_code=201,
        content={"success": True, "message": "Appointment created", "data": result.model_dump(mode="json")},
    )


# ⚠️ Register /queue BEFORE /{appointment_id} so FastAPI resolves it correctly
@router.get(
    "/queue",
    response_model=SuccessResponse[QueueResponse],
    dependencies=[Depends(require_permission(APPOINTMENT_READ))],
)
async def get_queue(current_user: AuthenticatedUser, db: DbSession) -> JSONResponse:
    """Today's waiting queue ordered by queue position."""
    service = AppointmentService(db)
    result = await service.get_queue(current_user.clinic_id)
    return JSONResponse(content={
        "success": True,
        "message": "Queue retrieved",
        "data": result.model_dump(mode="json"),
    })


@router.get(
    "",
    response_model=PaginatedResponse[AppointmentListItem],
    dependencies=[Depends(require_permission(APPOINTMENT_READ))],
)
async def list_appointments(
    current_user: AuthenticatedUser,
    db: DbSession,
    status: str | None = Query(None),
    appt_date: date | None = Query(None, alias="date"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    patient_id: uuid.UUID | None = Query(None),
    appointment_type: str | None = Query(None),
    search: str | None = Query(None, description="Search by appointment code"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> JSONResponse:
    """List appointments with filters: status, date, date range, patient, type, and code search."""
    filters = AppointmentFilter(
        status=status,
        appt_date=appt_date,
        date_from=date_from,
        date_to=date_to,
        patient_id=patient_id,
        appointment_type=appointment_type,
        search=search,
    )
    service = AppointmentService(db)
    result = await service.list_appointments(current_user.clinic_id, filters, page=page, per_page=per_page)
    return JSONResponse(content={
        "success": True,
        "message": "Appointments retrieved",
        "data": [item.model_dump(mode="json") for item in result.items],
        "meta": result.to_meta(),
    })


@router.get(
    "/{appointment_id}",
    response_model=SuccessResponse[AppointmentResponse],
    dependencies=[Depends(require_permission(APPOINTMENT_READ))],
)
async def get_appointment(
    appointment_id: uuid.UUID, current_user: AuthenticatedUser, db: DbSession
) -> JSONResponse:
    service = AppointmentService(db)
    result = await service.get_appointment(appointment_id, current_user.clinic_id)
    return JSONResponse(content={"success": True, "message": "Appointment retrieved", "data": result.model_dump(mode="json")})


@router.patch(
    "/{appointment_id}/confirm",
    response_model=SuccessResponse[AppointmentResponse],
    dependencies=[Depends(require_permission(APPOINTMENT_WRITE))],
)
async def confirm_appointment(
    appointment_id: uuid.UUID, current_user: AuthenticatedUser, db: DbSession
) -> JSONResponse:
    """Transition: pending → waiting. Assigns next queue position."""
    service = AppointmentService(db)
    result = await service.confirm_appointment(appointment_id, current_user.clinic_id, current_user)
    return JSONResponse(content={"success": True, "message": "Appointment confirmed", "data": result.model_dump(mode="json")})


@router.patch(
    "/{appointment_id}/cancel",
    response_model=SuccessResponse[AppointmentResponse],
    dependencies=[Depends(require_permission(APPOINTMENT_CANCEL))],
)
async def cancel_appointment(
    appointment_id: uuid.UUID,
    current_user: AuthenticatedUser,
    db: DbSession,
    body: AppointmentCancelRequest = Body(default_factory=AppointmentCancelRequest),
) -> JSONResponse:
    """Transition: pending|waiting → cancelled."""
    service = AppointmentService(db)
    result = await service.cancel_appointment(
        appointment_id, current_user.clinic_id, current_user, body.reason
    )
    return JSONResponse(content={"success": True, "message": "Appointment cancelled", "data": result.model_dump(mode="json")})


@router.patch(
    "/{appointment_id}/reschedule",
    response_model=SuccessResponse[AppointmentResponse],
    dependencies=[Depends(require_permission(APPOINTMENT_WRITE))],
)
async def reschedule_appointment(
    appointment_id: uuid.UUID,
    body: AppointmentRescheduleRequest,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Reschedule date/time. Resets waiting → pending and clears queue position."""
    service = AppointmentService(db)
    result = await service.reschedule_appointment(appointment_id, current_user.clinic_id, body)
    return JSONResponse(content={"success": True, "message": "Appointment rescheduled", "data": result.model_dump(mode="json")})


@router.patch(
    "/{appointment_id}/no-show",
    response_model=SuccessResponse[AppointmentResponse],
    dependencies=[Depends(require_permission(APPOINTMENT_WRITE))],
)
async def mark_no_show(
    appointment_id: uuid.UUID, current_user: AuthenticatedUser, db: DbSession
) -> JSONResponse:
    """Transition: waiting → no_show."""
    service = AppointmentService(db)
    result = await service.mark_no_show(appointment_id, current_user.clinic_id)
    return JSONResponse(content={"success": True, "message": "Appointment marked as no-show", "data": result.model_dump(mode="json")})


@router.patch(
    "/{appointment_id}/complete",
    response_model=SuccessResponse[AppointmentResponse],
    dependencies=[
        Depends(require_permission(APPOINTMENT_COMPLETE)),
        Depends(require_owner()),
    ],
)
async def complete_appointment(
    appointment_id: uuid.UUID, current_user: AuthenticatedUser, db: DbSession
) -> JSONResponse:
    """
    Transition: waiting → completed. Owner only.
    Normally called by consultation submit — direct use is for edge cases.
    """
    service = AppointmentService(db)
    result = await service.complete_appointment(appointment_id, current_user.clinic_id)
    return JSONResponse(content={"success": True, "message": "Appointment completed", "data": result.model_dump(mode="json")})
