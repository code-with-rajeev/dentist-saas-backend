# Standard library
import logging
import uuid

# Third-party
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

# Internal — dependencies
from app.dependencies import DbSession
from app.rbac.dependencies import AuthenticatedUser, require_owner, require_permission
from app.rbac.permissions import (
    CLINIC_SETTINGS_READ,
    CLINIC_SETTINGS_WRITE,
    CLINIC_STAFF_MANAGE,
)

# Internal — schemas + service
from app.schemas.clinic import (
    ClinicSettingsResponse,
    ClinicSettingsUpdate,
    StaffCreate,
    StaffPermissionsUpdate,
    StaffResponse,
)
from app.schemas.common import SuccessResponse
from app.services.clinic_service import ClinicService

router = APIRouter(prefix="/clinic", tags=["Clinic"])
logger = logging.getLogger(__name__)


# ============================================================
# Clinic Settings
# ============================================================

@router.get(
    "/settings",
    response_model=SuccessResponse[ClinicSettingsResponse],
    dependencies=[Depends(require_permission(CLINIC_SETTINGS_READ))],
)
async def get_clinic_settings(
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Retrieve clinic settings. Includes locked_fields list for the frontend."""
    service = ClinicService(db)
    result = await service.get_clinic_settings(current_user.clinic_id)
    return JSONResponse(content={
        "success": True,
        "message": "Clinic settings retrieved",
        "data": result.model_dump(mode="json"),
    })


@router.patch(
    "/settings",
    response_model=SuccessResponse[ClinicSettingsResponse],
    dependencies=[
        Depends(require_permission(CLINIC_SETTINGS_WRITE)),
        Depends(require_owner()),
    ],
)
async def update_clinic_settings(
    body: ClinicSettingsUpdate,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """
    Update editable clinic settings.
    Locked fields (name, gst_number, dentist_name, dentist_reg_id)
    are not accepted in this request — excluded from the schema.
    """
    service = ClinicService(db)
    result = await service.update_clinic_settings(current_user.clinic_id, body)
    return JSONResponse(content={
        "success": True,
        "message": "Clinic settings updated",
        "data": result.model_dump(mode="json"),
    })


# ============================================================
# Staff Management
# ============================================================

@router.get(
    "/staff",
    response_model=SuccessResponse[list[StaffResponse]],
    dependencies=[Depends(require_owner())],
)
async def list_staff(
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """List all active clinic staff members with their permissions."""
    service = ClinicService(db)
    results = await service.list_staff(current_user.clinic_id)
    return JSONResponse(content={
        "success": True,
        "message": "Staff list retrieved",
        "data": [r.model_dump(mode="json") for r in results],
    })


@router.post(
    "/staff",
    response_model=SuccessResponse[StaffResponse],
    status_code=201,
    dependencies=[Depends(require_owner())],
)
async def add_staff_member(
    body: StaffCreate,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Add a new staff member to the clinic with a role and optional permissions."""
    service = ClinicService(db)
    result = await service.add_staff_member(body, current_user.clinic_id, current_user)
    return JSONResponse(
        status_code=201,
        content={
            "success": True,
            "message": "Staff member added successfully",
            "data": result.model_dump(mode="json"),
        },
    )


@router.patch(
    "/staff/{staff_id}/permissions",
    response_model=SuccessResponse[StaffResponse],
    dependencies=[Depends(require_owner())],
)
async def update_staff_permissions(
    staff_id: uuid.UUID,
    body: StaffPermissionsUpdate,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Replace all permissions for a staff member atomically."""
    service = ClinicService(db)
    result = await service.update_staff_permissions(
        staff_id, current_user.clinic_id, body, current_user
    )
    return JSONResponse(content={
        "success": True,
        "message": "Staff permissions updated",
        "data": result.model_dump(mode="json"),
    })


@router.delete(
    "/staff/{staff_id}",
    response_model=SuccessResponse[None],
    dependencies=[Depends(require_owner())],
)
async def remove_staff_member(
    staff_id: uuid.UUID,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Soft-delete a staff member. Owner cannot be removed."""
    service = ClinicService(db)
    await service.remove_staff_member(staff_id, current_user.clinic_id)
    return JSONResponse(content={
        "success": True,
        "message": "Staff member removed",
        "data": None,
    })
